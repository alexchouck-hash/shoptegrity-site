"""Publication gate: nothing reaches the site as a fact unless it has a source.

Every record that leaves the generators passes through `gate_brand` or
`gate_healthcare`. The rules:

1. Modeled rows are refused. `industry_benchmark_model` rows describe invented
   entities. The generators contain none. `assert_no_synthetic` runs on the raw
   generator output before any gate, and a gate given such a row raises instead
   of relabelling it.

2. Claims need a per-claim source. A specific factual claim (counts, percentages,
   dates, ratios, legal or conduct characterizations, named owners, swap
   recommendations, text about named companies) is published only when the
   record's `claim_sources` has an entry for that field:

       "claim_sources": {
           "osha_violations_count": {
               "citation": "OSHA Establishment Search, inspections 2020-2025",
               "url": "https://www.osha.gov/ords/imis/establishment.html"
           }
       }

   Unsourced claims are set to None and listed in `withheld_claims` (field and
   reason only). Their values go to data/private/verification_queue.csv, where a
   claim_sources entry can restore them. That file is gitignored: the repository
   is public, so a tracked copy would publish every claim the site withholds.

3. SEC receipts (pipeline/sec_financials.py) back the parent identity, the
   ownership type, the filing link, and the shareholder payout and CEO pay shares
   of public filers. A receipt does not contain wage, marketing, cost-of-goods or
   clinical splits, so those need a claim_sources entry.

4. Ratings (composite_score, grade, labor_exploitation_rating, sweatshop_risk,
   waste_rating, rating_type, is_champion) are Shoptegrity opinions. The composite
   is computed by the rubric engine (rubric/engine.py) from cited inputs, and only
   when every rubric input is cited and every rubric dimension is scored. Ratings
   with no code path (grade, the categorical ratings) stay null. Hand-typed scores
   in the generators are not read.

5. data_provenance labels: verified_sec_filing needs a receipt. Any other label
   that asserts verification needs at least one per-claim http(s) source;
   otherwise the record is relabelled unverified.
"""

import csv
import copy
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pipeline.sec_financials import build_receipt, extract_cik, load_financials
from pipeline import osha_enforcement
from rubric.engine import compute_scores, load_rubric

ROOT = Path(__file__).resolve().parent.parent
# Gitignored (see .gitignore): it holds the withheld values verbatim.
QUEUE_PATH = ROOT / "data" / "private" / "verification_queue.csv"

SYNTHETIC_PROVENANCE = "industry_benchmark_model"
RECEIPT_PROVENANCE = "verified_sec_filing"
UNVERIFIED_PROVENANCE = "unverified"

# Ownership structures where zero shareholder payout is a structural fact, not an estimate.
NO_OUTSIDE_SHAREHOLDERS = {
    "cooperative", "worker_coop", "worker_esop", "purpose_trust", "nonprofit",
    "mutual", "government_public", "bcorp_nonprofit",
}
PHYSICIAN_OWNED = "physician_owned"

# Claim fields: published only with a claim_sources entry for the same field.
BRAND_CLAIM_FIELDS = [
    "osha_violations_count",
    "nlrb_complaints_count",
    "living_wage_certified",
    "labor_summary",
    "packaging_type",
    "repairability_score",
    "landfill_diverted_pct",
    "waste_summary",
    "swap_name",
    "swap_rationale",
    "swap_highlight",
    "champion_highlight",
    "parent_entity",
]

HEALTH_CLAIM_FIELDS = [
    "medical_loss_ratio_pct",
    "claims_denial_rate_pct",
    "charge_to_cost_ratio",
    "charity_care_pct",
    "regulatory_citations",
    "summary_notes",
    "is_pe_rollup",
    "pe_firm_name",
    "city",
    "state",
    "swap_name",
    "swap_rationale",
    # Sub-category and swap type characterize named owners and alternatives ("Wall Street", "Exemplary").
    "sub_category",
    "swap_type",
]

# Parent identity fields: a receipt or a per-claim source.
BRAND_OWNER_FIELDS = ["parent_company", "ownership_type"]
HEALTH_OWNER_FIELDS = ["parent_organization", "ownership_type", "ownership_tier"]

# Hand-typed receipt/retailer values that SEC XBRL does not provide.
RECEIPT_CLAIM_FIELDS = [
    "personnel_salaries_benefits_usd", "ceo_name", "median_worker_pay_usd",
    "ceo_pay_ratio", "regulatory_citations",
]
RETAILER_CLAIM_FIELDS = ["worker_wage_floor", "ceo_pay_ratio"]
RETAILER_FINANCIAL_FIELDS = ["annual_revenue", "net_income", "shareholder_payouts_annual", "ceo_pay"]

# Swap sub-fields: the score is a rating (never published from source literals); the
# experience and rationale text make claims about named companies.
SWAP_TEXT_FIELDS = ["experience", "rationale"]

def _public_name(name: Optional[str]) -> Optional[str]:
    """Display name without parenthetical descriptors such as "(Optum)", "(ESOPs)" or "(Co-op)".

    A descriptor inside a name is an ownership or affiliation claim, so it is removed rather than shown.
    """
    if name is None:
        return None
    return re.sub(r"\s*\([^()]*\)", "", name).strip()


RATING_FIELDS = ["composite_score", "grade", "labor_exploitation_rating", "sweatshop_risk", "waste_rating"]
BRAND_CATEGORICAL_RATINGS = ["labor_exploitation_rating", "sweatshop_risk", "waste_rating"]

# Inputs the rubric composite needs, and the rubric dimension each one scores.
# The rubric scores a dimension only from cited evidence, so each input is passed to
# compute_scores as an evidence item carrying its citation. Any unpublished input,
# or any unscored dimension, withholds the composite.
RUBRIC_DIMENSION_FOR_FIELD = {
    "ownership_type": "ownership",
    "shareholder_extraction_pct": "capital_extraction",
    "ceo_pay_ratio": "pay_equity",
    "osha_violations_count": "labor",
    "nlrb_complaints_count": "labor",
    "living_wage_certified": "labor",
    "landfill_diverted_pct": "environment",
    "waste_summary": "environment",
    "locality_tier": "locality",
}
RUBRIC_INPUTS = list(RUBRIC_DIMENSION_FOR_FIELD)

# Columns the seeds must allow to hold NULL once gated (see allow_null_columns).
BRAND_GATED_COLUMNS = [
    "parent_company", "ownership_type", "composite_score", "grade",
    "labor_exploitation_rating", "sweatshop_risk", "waste_rating",
]
HEALTH_GATED_COLUMNS = [
    "parent_organization", "ownership_type", "ownership_tier", "sub_category", "composite_score", "grade",
]

RATING_TYPE = "Shoptegrity opinion rating under the published rubric (see /methodology)"

_RUBRIC_CACHE: Dict[str, Any] = {}
_OSHA_CACHE: Dict[str, Any] = {}


def has_source(sources: Optional[Dict[str, Any]], field: str) -> bool:
    src = (sources or {}).get(field)
    return bool(
        isinstance(src, dict)
        and str(src.get("citation", "")).strip()
        and str(src.get("url", "")).startswith(("http://", "https://"))
    )


def _has_url_source(sources: Optional[Dict[str, Any]]) -> bool:
    return any(has_source(sources, field) for field in (sources or {}))


def assert_no_synthetic(records: List[Dict[str, Any]], dataset: str) -> None:
    """Run on raw generator output, before any gate. Fails the build on modeled or '#123'-style rows."""
    bad = [
        r.get("name", "?") for r in records
        if r.get("data_provenance") == SYNTHETIC_PROVENANCE
        or re.search(
            r"#\d+",
            f"{r.get('name', '')} {r.get('parent_company') or r.get('parent_organization') or ''}",
        )
    ]
    if bad:
        raise ValueError(f"{dataset}: refusing to publish {len(bad)} generated records, e.g. {bad[:3]}")


def allow_null_columns(table: Any, names: List[str]) -> None:
    """Let a table that a seed recreates hold NULL in gated columns.

    The models declare these columns NOT NULL. A gated value is withheld as None,
    so the seed relaxes the constraint on the table it is about to create.
    Remove this once the models declare the columns Optional.
    """
    for name in names:
        table.c[name].nullable = True


def _refuse_modeled(rec: Dict[str, Any]) -> None:
    if rec.get("data_provenance") == SYNTHETIC_PROVENANCE:
        raise ValueError(
            f"{rec.get('name', '?')}: {SYNTHETIC_PROVENANCE} rows are refused; delete the generator row"
        )


def _withhold(withheld: List[Dict[str, Any]], field: str, value: Any, reason: str) -> None:
    if value in (None, [], ""):
        return
    withheld.append({"field": field, "value": value, "reason": reason})


def _rating_withheld(withheld: List[Dict[str, Any]], field: str, reason: str) -> None:
    withheld.append({"field": field, "value": None, "reason": reason})


def _gate_fields(rec: Dict[str, Any], fields: List[str], sources: Dict[str, Any], withheld: List[Dict[str, Any]]) -> None:
    for field in fields:
        if field in rec and not has_source(sources, field):
            _withhold(withheld, field, rec[field], "no per-claim source")
            rec[field] = [] if isinstance(rec[field], list) else None


def _gate_owner_field(rec: Dict[str, Any], field: str, receipt: Optional[Dict[str, Any]],
                      sources: Dict[str, Any], withheld: List[Dict[str, Any]]) -> None:
    if field not in rec or receipt is not None or has_source(sources, field):
        return
    _withhold(withheld, field, rec[field], "no SEC receipt or per-claim source")
    rec[field] = None


def _claim_only_split(rec: Dict[str, Any], field: str, sources: Dict[str, Any],
                      basis: Dict[str, str], withheld: List[Dict[str, Any]]) -> None:
    value = rec.get(field)
    if value is not None and has_source(sources, field):
        basis[field] = "claim_source"
        return
    _withhold(withheld, field, value, "no per-claim source")
    rec[field] = None


def _filed_or_cited_split(rec: Dict[str, Any], field: str, filed: Optional[float], filed_basis: str,
                          sources: Dict[str, Any], basis: Dict[str, str], withheld: List[Dict[str, Any]]) -> None:
    if filed is not None:
        rec[field] = filed
        basis[field] = filed_basis
        return
    value = rec.get(field)
    if value is not None and has_source(sources, field):
        rec[field] = value
        basis[field] = "claim_source"
        return
    _withhold(withheld, field, value, "no filing or per-claim source")
    rec[field] = None


def _set_residual(rec: Dict[str, Any], field: str, parts: List[str],
                  basis: Dict[str, str], withheld: List[Dict[str, Any]]) -> None:
    old = rec.get(field)
    value = _residual([rec.get(p) for p in parts])
    rec[field] = value
    if value is not None:
        basis[field] = "residual"
    elif old is not None:
        _withhold(withheld, field, old, "residual needs every input published")


def _receipt_for(parent: Optional[str], financials: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    cik = extract_cik(parent)
    fin = financials.get(cik) if cik else None
    if not fin or fin.get("error"):
        return None
    return build_receipt(fin)


# Words that carry no identity ("Walmart Inc." and "Walmart" are the same company).
_NAME_STOPWORDS = {"the", "inc", "incorporated", "co", "corp", "corporation", "company", "llc", "ltd",
                   "plc", "group", "holdings", "holding", "and", "of"}


def _same_company(record_name: Optional[str], filer_name: Optional[str]) -> bool:
    """True when every distinctive word of the record's name appears in the filer's legal name."""
    record = {w for w in re.findall(r"[a-z0-9]+", (record_name or "").lower()) if w not in _NAME_STOPWORDS}
    filer = set(re.findall(r"[a-z0-9]+", (filer_name or "").lower()))
    return bool(record) and record <= filer


def _receipt_for_record(rec: Dict[str, Any], parent: Optional[str], financials: Dict[str, Dict[str, Any]],
                        sources: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """A parent's filing backs a record only when the record is the filer itself, or its parent link is cited.

    A filing for General Mills does not show that Cheerios belongs to General Mills, so the
    filed payout and CEO pay figures are not carried onto the brand either.
    """
    receipt = _receipt_for(parent, financials)
    if receipt is None:
        return None
    if has_source(sources, "parent_company") or has_source(sources, "parent_organization"):
        return receipt
    if _same_company(rec.get("name"), receipt.get("entity_name")):
        return receipt
    return None


def _residual(values: List[Optional[float]]) -> Optional[float]:
    """100 minus the parts, computed only when every part is published."""
    if any(v is None for v in values):
        return None
    return round(max(0.0, 100.0 - sum(values)), 1)


def _provenance_label(label: Optional[str], has_receipt: bool, sources: Dict[str, Any]) -> str:
    if has_receipt:
        return RECEIPT_PROVENANCE
    if label in (None, "", UNVERIFIED_PROVENANCE, RECEIPT_PROVENANCE):
        return UNVERIFIED_PROVENANCE
    return label if _has_url_source(sources) else UNVERIFIED_PROVENANCE


def _gate_swap(swap: Any, prefix: str, sources: Dict[str, Any], withheld: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(swap, dict):
        return None
    out = dict(swap)
    # A ranked option is shown only when the option itself is cited (its name is a claim about a named company)
    if out.get("name") is not None and not (
        has_source(sources, f"{prefix}.name") or has_source(sources, f"{prefix}.rationale")
    ):
        _withhold(withheld, f"{prefix}.name", out["name"], "ranked option: no per-claim source")
        return None
    if out.get("score") is not None:
        _withhold(withheld, f"{prefix}.score", out["score"], "rating: no rubric path for swap scores")
    out["score"] = None
    for key in SWAP_TEXT_FIELDS:
        value = out.get(key)
        if value is not None and not has_source(sources, f"{prefix}.{key}"):
            _withhold(withheld, f"{prefix}.{key}", value, "no per-claim source")
            out[key] = None
    # Price text compares or prices named alternatives, so it is a claim too.
    price = out.get("price_level")
    if price is not None and not has_source(sources, f"{prefix}.price_level"):
        _withhold(withheld, f"{prefix}.price_level", price, "no per-claim source")
        out["price_level"] = None
    return out


def _rubric() -> Dict[str, Any]:
    if "rubric" not in _RUBRIC_CACHE:
        _RUBRIC_CACHE["rubric"] = load_rubric()
    return _RUBRIC_CACHE["rubric"]


def _cite(sources: Dict[str, Any], key: str, source_type: str = "manual") -> Optional[Tuple[str, str]]:
    """(url, source_type) when a per-claim source backs key, otherwise None."""
    return (sources[key]["url"], source_type) if has_source(sources, key) else None


def _rubric_inputs(rec: Dict[str, Any], sources: Dict[str, Any], receipt: Optional[Dict[str, Any]],
                   ceo_pay_ratio: Optional[float]) -> Dict[str, Tuple[Any, Optional[Tuple[str, str]]]]:
    """Each rubric input as (published value, citation). The value is None unless it is published."""
    receipt_cite = (receipt["filing_url"], "sec_edgar") if receipt else None
    payout_filed = bool(receipt and receipt.get("shareholder_payout_pct_of_revenue") is not None)
    if payout_filed:
        shareholder_cite = receipt_cite
    else:
        # A structural zero is cited through the ownership claim that establishes it.
        shareholder_cite = _cite(sources, "shareholder_extraction_pct") or _cite(sources, "ownership_type") or receipt_cite
    return {
        "ownership_type": (rec.get("ownership_type"), receipt_cite or _cite(sources, "ownership_type")),
        "shareholder_extraction_pct": (rec.get("shareholder_extraction_pct"), shareholder_cite),
        "ceo_pay_ratio": (ceo_pay_ratio, _cite(sources, "sec_receipt_details.ceo_pay_ratio")),
        "osha_violations_count": (rec.get("osha_violations_count"), _cite(sources, "osha_violations_count", "osha")),
        "nlrb_complaints_count": (rec.get("nlrb_complaints_count"), _cite(sources, "nlrb_complaints_count")),
        "living_wage_certified": (rec.get("living_wage_certified"), _cite(sources, "living_wage_certified")),
        "landfill_diverted_pct": (rec.get("landfill_diverted_pct"), _cite(sources, "landfill_diverted_pct")),
        "waste_summary": (rec.get("waste_summary"), _cite(sources, "waste_summary")),
        "locality_tier": (rec.get("locality_tier"), _cite(sources, "locality_tier")),
    }


def _composite(rec: Dict[str, Any], inputs: Dict[str, Tuple[Any, Optional[Tuple[str, str]]]]) -> Tuple[Optional[float], List[str]]:
    """Rubric composite computed from cited inputs. Returns (None, reasons) unless every input and dimension is scored."""
    unpublished = [f for f in RUBRIC_INPUTS if inputs[f][0] is None or inputs[f][1] is None]
    if unpublished:
        return None, ["rubric inputs not published: " + ", ".join(unpublished)]

    values = {f: inputs[f][0] for f in RUBRIC_INPUTS}
    evidence = [
        {
            "dimension": RUBRIC_DIMENSION_FOR_FIELD[f],
            "source_url": inputs[f][1][0],
            "source_type": inputs[f][1][1],
            "impact": 0,  # no reviewer-assigned impacts exist; the signals below carry the labor points
            "field": f,
        }
        for f in RUBRIC_INPUTS
    ]
    signals = []
    if values["living_wage_certified"] is True:
        signals.append("living_wage_certified")
    if values["osha_violations_count"] > 0:
        signals.append("osha_serious_violation")
    if values["nlrb_complaints_count"] > 0:
        signals.append("nlrb_violation")
    company = {
        "id": str(rec.get("id") or rec.get("name") or ""),
        "name": str(rec.get("name") or ""),
        "ownership_type": values["ownership_type"],
        "locality_tier": values["locality_tier"],
        "ceo_pay_ratio": values["ceo_pay_ratio"],
        "capital_extraction_ratio": values["shareholder_extraction_pct"] / 100.0,
        "labor_signals": signals,
        "env_signals": [],
    }
    result = compute_scores(company, evidence, _rubric())
    unscored = [key for key, dim in result.dimensions.items() if dim.value is None]
    if unscored:
        return None, ["rubric dimensions not scored: " + ", ".join(unscored)]
    return result.composite_score, []


def _apply_ratings(rec: Dict[str, Any], inputs: Dict[str, Tuple[Any, Optional[Tuple[str, str]]]],
                   withheld: List[Dict[str, Any]], categorical: List[str]) -> Optional[float]:
    composite, reasons = _composite(rec, inputs)
    rec["composite_score"] = composite
    if composite is None:
        _rating_withheld(withheld, "composite_score", reasons[0])
    rec["grade"] = None
    _rating_withheld(
        withheld, "grade",
        "no published composite_score" if composite is None else "no grade band table in code",
    )
    for field in categorical:
        rec[field] = None
        _rating_withheld(withheld, field, "no code computes this rating from cited inputs")
    rec["rating_type"] = RATING_TYPE if composite is not None else None
    return composite


def _finish(rec: Dict[str, Any], basis: Dict[str, str], withheld: List[Dict[str, Any]]) -> Dict[str, Any]:
    rec["split_basis"] = basis
    # Public output names the withheld fields but never their values.
    rec["withheld_claims"] = [{"field": w["field"], "reason": w["reason"]} for w in withheld]
    rec["_withheld"] = withheld  # internal: values go to the verification queue only
    return rec


def _osha_data() -> Dict[str, Dict[str, Any]]:
    if "data" not in _OSHA_CACHE:
        _OSHA_CACHE["data"] = osha_enforcement.load_enforcement()
    return _OSHA_CACHE["data"]


def gate_brand(src: Dict[str, Any], financials: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    _refuse_modeled(src)
    rec = copy.deepcopy(src)
    rec["name"] = _public_name(rec.get("name"))
    withheld: List[Dict[str, Any]] = []
    basis: Dict[str, str] = {}
    rec["claim_sources"] = dict(rec.get("claim_sources") or {})
    sources = rec["claim_sources"]

    # Look up the receipt and OSHA match by the original parent name, before any field is withheld.
    receipt = _receipt_for_record(rec, rec.get("parent_company"), financials, sources)

    # OSHA counts from DOL enforcement data replace hand-typed ones once a person has
    # approved the establishment-name match (pipeline/osha_enforcement.py).
    osha = osha_enforcement.published_record_for(rec.get("parent_company"), _osha_data())
    rec["osha_enforcement"] = None
    if osha:
        rec["osha_violations_count"] = osha["violations"]
        sources["osha_violations_count"] = osha_enforcement.claim_source(osha)
        rec["osha_enforcement"] = osha_enforcement.public_summary(osha)

    for field in BRAND_OWNER_FIELDS:
        _gate_owner_field(rec, field, receipt, sources, withheld)
    _gate_fields(rec, BRAND_CLAIM_FIELDS, sources, withheld)

    old_receipt = rec.get("sec_receipt_details") or {}
    for f in RECEIPT_CLAIM_FIELDS:
        if f in old_receipt and not has_source(sources, f"sec_receipt_details.{f}"):
            _withhold(withheld, f"sec_receipt_details.{f}", old_receipt[f], "not in SEC XBRL data; needs citation")

    rec["sec_receipt_details"] = receipt
    if receipt:
        rec["sec_url"] = receipt["filing_url"]
    else:
        _gate_fields(rec, ["sec_url"], sources, withheld)
    rec["data_provenance"] = _provenance_label(rec.get("data_provenance"), receipt is not None, sources)

    # Retailer box: financial lines from the filing, everything else needs a citation.
    rd = rec.get("retailer_details")
    if rd:
        for f in RETAILER_FINANCIAL_FIELDS:
            if f in rd:
                old = rd[f]
                rd[f] = None
                if receipt:
                    rd[f] = {
                        "annual_revenue": receipt["total_revenue_usd"],
                        "net_income": receipt["net_income_usd"],
                        "shareholder_payouts_annual": receipt["total_shareholder_payout_usd"],
                        "ceo_pay": receipt["ceo_compensation_usd"],
                    }[f]
                elif not has_source(sources, f"retailer_details.{f}"):
                    _withhold(withheld, f"retailer_details.{f}", old, "no filing or citation")
                else:
                    rd[f] = old
        for f in RETAILER_CLAIM_FIELDS:
            if f in rd and not has_source(sources, f"retailer_details.{f}"):
                _withhold(withheld, f"retailer_details.{f}", rd[f], "no per-claim source")
                rd[f] = None
        if "swap_highlight" in rd and not has_source(sources, "retailer_details.swap_highlight"):
            _withhold(withheld, "retailer_details.swap_highlight", rd["swap_highlight"], "no per-claim source")
            rd["swap_highlight"] = None
        for key in ("better_swap", "best_swap"):
            if key in rd:
                rd[key] = _gate_swap(rd[key], f"retailer_details.{key}", sources, withheld)
        if receipt:
            rd["fiscal_year_end"] = receipt["fiscal_year_end"]
            rd["filing_url"] = receipt["filing_url"]

    for key in ("better_swap", "best_swap"):
        if key in rec:
            rec[key] = _gate_swap(rec[key], key, sources, withheld)

    # Dollar split: filed numbers where a receipt covers them; otherwise a per-claim source.
    ownership_type = rec.get("ownership_type")
    filed_payout = (
        round(receipt["shareholder_payout_pct_of_revenue"], 1)
        if receipt and receipt.get("shareholder_payout_pct_of_revenue") is not None else None
    )
    if filed_payout is None and ownership_type in NO_OUTSIDE_SHAREHOLDERS:
        rec["shareholder_extraction_pct"] = 0.0
        basis["shareholder_extraction_pct"] = "ownership_structure"
    else:
        _filed_or_cited_split(rec, "shareholder_extraction_pct", filed_payout, "sec_filing", sources, basis, withheld)

    filed_ceo = (
        round(receipt["ceo_pay_pct_of_revenue"], 3)
        if receipt and receipt.get("ceo_pay_pct_of_revenue") is not None else None
    )
    _filed_or_cited_split(rec, "exec_comp_pct", filed_ceo, "sec_filing_ceo_only", sources, basis, withheld)

    # A receipt has no wage, marketing or cost-of-goods figures, so these need a per-claim source.
    for field in ("worker_wages_pct", "marketing_ads_pct", "cogs_supply_pct"):
        _claim_only_split(rec, field, sources, basis, withheld)

    _set_residual(
        rec, "retained_operations_pct",
        ["worker_wages_pct", "exec_comp_pct", "shareholder_extraction_pct", "marketing_ads_pct", "cogs_supply_pct"],
        basis, withheld,
    )

    ceo_ratio = old_receipt.get("ceo_pay_ratio") if has_source(sources, "sec_receipt_details.ceo_pay_ratio") else None
    inputs = _rubric_inputs(rec, sources, receipt, ceo_ratio)
    composite = _apply_ratings(rec, inputs, withheld, BRAND_CATEGORICAL_RATINGS)

    if "is_champion" in rec:
        claimed = bool(rec["is_champion"])
        rec["is_champion"] = claimed and composite is not None and composite >= 90
        if claimed and not rec["is_champion"]:
            _withhold(withheld, "is_champion", True, "champion status needs a published composite_score of 90 or more")

    return _finish(rec, basis, withheld)


def gate_healthcare(src: Dict[str, Any], financials: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    _refuse_modeled(src)
    rec = copy.deepcopy(src)
    rec["name"] = _public_name(rec.get("name"))
    withheld: List[Dict[str, Any]] = []
    basis: Dict[str, str] = {}
    rec["claim_sources"] = dict(rec.get("claim_sources") or {})
    sources = rec["claim_sources"]

    receipt = _receipt_for_record(rec, rec.get("parent_organization"), financials, sources)
    rec["sec_receipt_details"] = receipt

    for field in HEALTH_OWNER_FIELDS:
        _gate_owner_field(rec, field, receipt, sources, withheld)
    _gate_fields(rec, HEALTH_CLAIM_FIELDS, sources, withheld)

    if receipt:
        rec["filing_url"] = receipt["filing_url"]
        rec["source_citation"] = (
            f"{receipt['entity_name']} Form 10-K, fiscal year ended {receipt['fiscal_year_end']} "
            f"(SEC accession {receipt['accession']})"
        )
    else:
        _gate_fields(rec, ["filing_url", "source_citation"], sources, withheld)
    rec["data_provenance"] = _provenance_label(rec.get("data_provenance"), receipt is not None, sources)

    ownership_type = rec.get("ownership_type")
    filed_payout = (
        round(receipt["shareholder_payout_pct_of_revenue"], 1)
        if receipt and receipt.get("shareholder_payout_pct_of_revenue") is not None else None
    )
    if filed_payout is None and ownership_type in (NO_OUTSIDE_SHAREHOLDERS | {PHYSICIAN_OWNED}):
        rec["shareholder_extraction_pct"] = 0.0
        basis["shareholder_extraction_pct"] = "ownership_structure"
    else:
        _filed_or_cited_split(rec, "shareholder_extraction_pct", filed_payout, "sec_filing", sources, basis, withheld)

    filed_ceo = (
        round(receipt["ceo_pay_pct_of_revenue"], 3)
        if receipt and receipt.get("ceo_pay_pct_of_revenue") is not None else None
    )
    _filed_or_cited_split(rec, "exec_comp_pct", filed_ceo, "sec_filing_ceo_only", sources, basis, withheld)

    for field in ("clinical_care_wages_pct", "admin_overhead_pct"):
        _claim_only_split(rec, field, sources, basis, withheld)

    _set_residual(
        rec, "supplies_operations_pct",
        ["clinical_care_wages_pct", "admin_overhead_pct", "exec_comp_pct", "shareholder_extraction_pct"],
        basis, withheld,
    )

    inputs = _rubric_inputs(rec, sources, receipt, None)
    _apply_ratings(rec, inputs, withheld, [])

    return _finish(rec, basis, withheld)


def public_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Strip internal keys before anything is written to a published file."""
    return {k: v for k, v in rec.items() if not k.startswith("_")}


def write_verification_queue(datasets: Dict[str, List[Dict[str, Any]]], path: Path = QUEUE_PATH) -> int:
    """CSV backlog of every withheld claim. Add a claim_sources entry to restore one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    seen = set()
    for dataset, records in datasets.items():
        for r in records:
            owner = r.get("parent_company") or r.get("parent_organization") or ""
            for w in r.get("_withheld") or []:
                # Sub-brands share their parent's claims; list each parent claim once.
                key = (dataset, owner, w["field"], str(w["value"]))
                if key in seen:
                    continue
                seen.add(key)
                rows.append({
                    "dataset": dataset,
                    "record": r["name"],
                    "owner": owner,
                    "field": w["field"],
                    "withheld_value": w["value"] if not isinstance(w["value"], list) else " | ".join(map(str, w["value"])),
                    "reason": w["reason"],
                })
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["dataset", "record", "owner", "field", "withheld_value", "reason"])
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


__all__ = [
    "gate_brand", "gate_healthcare", "write_verification_queue", "assert_no_synthetic", "public_record",
    "allow_null_columns", "load_financials", "has_source",
    "BRAND_GATED_COLUMNS", "HEALTH_GATED_COLUMNS", "RATING_FIELDS",
]


if __name__ == "__main__":
    from pipeline.top2000_brands import generate_top_2000_brands
    from pipeline.healthcare_2000 import generate_healthcare_2000

    n = write_verification_queue({"brands": generate_top_2000_brands(), "healthcare": generate_healthcare_2000()})
    print(f"Wrote {n} withheld claims to {QUEUE_PATH}")
