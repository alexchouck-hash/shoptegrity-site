"""Publication gate: nothing reaches the site as a fact unless it has a source.

Every record that leaves the pipeline passes through `gate_brand` or
`gate_healthcare`. The rules:

1. Synthetic records (`industry_benchmark_model` rows that describe invented
   entities) are never published. The generators no longer create them, and
   `assert_no_synthetic` fails the build if one slips back in.

2. Specific factual claims (OSHA/NLRB counts, denial rates, markups,
   enforcement actions, narrative summaries, PE sponsor names, ...) are
   published only when the record carries a citation for that field:

       "claim_sources": {
           "osha_violations_count": {
               "citation": "OSHA Establishment Search, inspections 2020-2025",
               "url": "https://www.osha.gov/ords/imis/establishment.html"
           }
       }

   Unsourced claims are set to None and listed in `withheld_claims`; they are
   also written to data/verification_queue.csv so they can be sourced and
   restored.

3. OSHA violation counts come from DOL enforcement data
   (pipeline/osha_enforcement.py), published only after the matched
   establishment names have been reviewed and approved.

4. Public-company dollar figures come from SEC XBRL data
   (pipeline/sec_financials.py), never from hand-typed values. Shareholder
   payout % and CEO pay % are derived from those filed numbers. The other
   dollar-split segments are labelled as estimates in `split_basis`.

5. Grades and ratings (composite_score, grade, labor_exploitation_rating,
   waste_rating, sweatshop_risk) are Shoptegrity opinions under the published
   rubric and are marked as such with `rating_type`.
"""

import csv
import re
import copy
from pathlib import Path
from typing import Any, Dict, List, Optional

from pipeline.sec_financials import build_receipt, extract_cik, load_financials
from pipeline import osha_enforcement

ROOT = Path(__file__).resolve().parent.parent
QUEUE_PATH = ROOT / "data" / "verification_queue.csv"

SYNTHETIC_PROVENANCE = "industry_benchmark_model"

# Ownership structures where zero shareholder payout is a structural fact, not an estimate.
NO_OUTSIDE_SHAREHOLDERS = {
    "cooperative", "worker_coop", "worker_esop", "purpose_trust", "nonprofit",
    "mutual", "government_public", "bcorp_nonprofit",
}

BRAND_CLAIM_FIELDS = [
    "osha_violations_count",
    "nlrb_complaints_count",
    "living_wage_certified",
    "labor_summary",
    "packaging_type",
    "repairability_score",
    "landfill_diverted_pct",
    "waste_summary",
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
]

# Hand-typed receipt/retailer values that SEC XBRL does not provide.
RECEIPT_CLAIM_FIELDS = [
    "personnel_salaries_benefits_usd", "ceo_name", "median_worker_pay_usd",
    "ceo_pay_ratio", "regulatory_citations",
]
RETAILER_CLAIM_FIELDS = ["worker_wage_floor", "ceo_pay_ratio"]
RETAILER_FINANCIAL_FIELDS = ["annual_revenue", "net_income", "shareholder_payouts_annual", "ceo_pay"]

RATING_TYPE = "Shoptegrity opinion rating under the published rubric (see /methodology)"


def has_source(sources: Dict[str, Any], field: str) -> bool:
    src = (sources or {}).get(field)
    return bool(
        isinstance(src, dict)
        and str(src.get("citation", "")).strip()
        and str(src.get("url", "")).startswith(("http://", "https://"))
    )


def assert_no_synthetic(records: List[Dict[str, Any]], dataset: str) -> None:
    """Run after gating. Benchmark-model labels and '#123'-style names mark invented entities."""
    bad = [
        r["name"] for r in records
        if r.get("data_provenance") == SYNTHETIC_PROVENANCE
        or re.search(r"#\d+", r.get("name", "") + " " + str(r.get("parent_company") or r.get("parent_organization") or ""))
    ]
    if bad:
        raise ValueError(f"{dataset}: refusing to publish {len(bad)} generated records, e.g. {bad[:3]}")


def _withhold(rec: Dict[str, Any], field: str, value: Any, withheld: List[Dict[str, Any]], reason: str) -> None:
    if value in (None, [], ""):
        return
    withheld.append({"field": field, "value": value, "reason": reason})


def _gate_fields(rec: Dict[str, Any], fields: List[str], withheld: List[Dict[str, Any]]) -> None:
    sources = rec.get("claim_sources") or {}
    for field in fields:
        if field in rec and not has_source(sources, field):
            _withhold(rec, field, rec[field], withheld, "no per-claim source")
            rec[field] = [] if isinstance(rec[field], list) else None


def _receipt_for(parent: Optional[str], financials: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    cik = extract_cik(parent)
    fin = financials.get(cik) if cik else None
    if not fin or fin.get("error"):
        return None
    return build_receipt(fin)


def _residual(rec: Dict[str, Any], parts: List[str]) -> Optional[float]:
    vals = [rec.get(p) for p in parts]
    if any(v is None for v in vals):
        return None
    return round(max(0.0, 100.0 - sum(vals)), 1)


def gate_brand(src: Dict[str, Any], financials: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    rec = copy.deepcopy(src)
    withheld: List[Dict[str, Any]] = []
    basis: Dict[str, str] = {}
    sources = rec.setdefault("claim_sources", {})
    modeled = rec.get("data_provenance") == SYNTHETIC_PROVENANCE

    # OSHA counts from DOL enforcement data replace hand-typed ones once a person has
    # approved the establishment-name match (pipeline/osha_enforcement.py).
    osha = osha_enforcement.published_record_for(rec.get("parent_company"), _osha_data())
    rec["osha_enforcement"] = None
    if osha:
        rec["osha_violations_count"] = osha["violations"]
        sources["osha_violations_count"] = osha_enforcement.claim_source(osha)
        rec["osha_enforcement"] = osha_enforcement.public_summary(osha)

    _gate_fields(rec, BRAND_CLAIM_FIELDS, withheld)

    old_receipt = rec.get("sec_receipt_details") or {}
    for f in RECEIPT_CLAIM_FIELDS:
        if f in old_receipt and not has_source(sources, f"sec_receipt_details.{f}"):
            _withhold(rec, f"sec_receipt_details.{f}", old_receipt[f], withheld, "not in SEC XBRL data; needs citation")

    receipt = _receipt_for(rec.get("parent_company"), financials)
    rec["sec_receipt_details"] = receipt
    if receipt:
        rec["sec_url"] = receipt["filing_url"]
        rec["data_provenance"] = "verified_sec_filing"
    elif rec.get("data_provenance") in ("verified_sec_filing", SYNTHETIC_PROVENANCE):
        rec["data_provenance"] = "unverified"
        rec["sec_url"] = None

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
                    _withhold(rec, f"retailer_details.{f}", old, withheld, "no filing or citation")
                else:
                    rd[f] = old
        for f in RETAILER_CLAIM_FIELDS:
            if f in rd and not has_source(sources, f"retailer_details.{f}"):
                _withhold(rec, f"retailer_details.{f}", rd[f], withheld, "no per-claim source")
                rd[f] = None
        if receipt:
            rd["fiscal_year_end"] = receipt["fiscal_year_end"]
            rd["filing_url"] = receipt["filing_url"]

    # Dollar split: filed numbers where we have them, labelled estimates otherwise.
    if receipt and receipt.get("shareholder_payout_pct_of_revenue") is not None:
        rec["shareholder_extraction_pct"] = round(receipt["shareholder_payout_pct_of_revenue"], 1)
        basis["shareholder_extraction_pct"] = "sec_filing"
    elif rec.get("ownership_type") in NO_OUTSIDE_SHAREHOLDERS:
        rec["shareholder_extraction_pct"] = 0.0
        basis["shareholder_extraction_pct"] = "ownership_structure"
    elif rec.get("shareholder_extraction_pct") is not None:
        _withhold(rec, "shareholder_extraction_pct", rec["shareholder_extraction_pct"], withheld, "no filing")
        rec["shareholder_extraction_pct"] = None

    if receipt and receipt.get("ceo_pay_pct_of_revenue") is not None:
        rec["exec_comp_pct"] = round(receipt["ceo_pay_pct_of_revenue"], 3)
        basis["exec_comp_pct"] = "sec_filing_ceo_only"
    else:
        _withhold(rec, "exec_comp_pct", rec.get("exec_comp_pct"), withheld, "no filing")
        rec["exec_comp_pct"] = None

    for f in ("worker_wages_pct", "marketing_ads_pct", "cogs_supply_pct"):
        if modeled and not receipt:
            _withhold(rec, f, rec.get(f), withheld, "modeled, not from a filing")
            rec[f] = None
        elif rec.get(f) is not None:
            basis[f] = "estimate"
    rec["retained_operations_pct"] = _residual(
        {**rec, "exec_comp_pct": rec.get("exec_comp_pct") or 0.0,
         "shareholder_extraction_pct": rec.get("shareholder_extraction_pct") or 0.0},
        ["worker_wages_pct", "exec_comp_pct", "shareholder_extraction_pct", "marketing_ads_pct", "cogs_supply_pct"],
    )
    basis["retained_operations_pct"] = "residual"

    return _finish(rec, basis, withheld)


_OSHA_CACHE: Dict[str, Any] = {}


def _osha_data() -> Dict[str, Dict[str, Any]]:
    if "data" not in _OSHA_CACHE:
        _OSHA_CACHE["data"] = osha_enforcement.load_enforcement()
    return _OSHA_CACHE["data"]


def gate_healthcare(src: Dict[str, Any], financials: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    rec = copy.deepcopy(src)
    withheld: List[Dict[str, Any]] = []
    basis: Dict[str, str] = {}
    rec.setdefault("claim_sources", {})
    modeled = rec.get("data_provenance") == SYNTHETIC_PROVENANCE

    _gate_fields(rec, HEALTH_CLAIM_FIELDS, withheld)

    receipt = _receipt_for(rec.get("parent_organization"), financials)
    rec["sec_receipt_details"] = receipt
    if receipt:
        rec["data_provenance"] = "verified_sec_filing"
        rec["filing_url"] = receipt["filing_url"]
        rec["source_citation"] = (
            f"{receipt['entity_name']} Form 10-K, fiscal year ended {receipt['fiscal_year_end']} "
            f"(SEC accession {receipt['accession']})"
        )
    elif modeled:
        rec["data_provenance"] = "ownership_profile"
        rec["source_citation"] = None
        rec["filing_url"] = None
    elif rec.get("data_provenance") == "verified_sec_filing":
        rec["data_provenance"] = "unverified"

    split = ["clinical_care_wages_pct", "admin_overhead_pct", "exec_comp_pct",
             "shareholder_extraction_pct", "supplies_operations_pct"]
    if modeled:
        # Modeled numbers about a real company are not publishable at all.
        for f in split:
            _withhold(rec, f, rec.get(f), withheld, "modeled, not from a filing")
            rec[f] = None
    else:
        if receipt and receipt.get("shareholder_payout_pct_of_revenue") is not None:
            rec["shareholder_extraction_pct"] = round(receipt["shareholder_payout_pct_of_revenue"], 1)
            basis["shareholder_extraction_pct"] = "sec_filing"
        elif rec.get("ownership_type") in NO_OUTSIDE_SHAREHOLDERS or rec.get("ownership_type") == "physician_owned":
            rec["shareholder_extraction_pct"] = 0.0
            basis["shareholder_extraction_pct"] = "ownership_structure"
        else:
            _withhold(rec, "shareholder_extraction_pct", rec.get("shareholder_extraction_pct"), withheld, "no filing")
            rec["shareholder_extraction_pct"] = None

        if receipt and receipt.get("ceo_pay_pct_of_revenue") is not None:
            rec["exec_comp_pct"] = round(receipt["ceo_pay_pct_of_revenue"], 3)
            basis["exec_comp_pct"] = "sec_filing_ceo_only"
        else:
            _withhold(rec, "exec_comp_pct", rec.get("exec_comp_pct"), withheld, "no filing")
            rec["exec_comp_pct"] = None

        for f in ("clinical_care_wages_pct", "admin_overhead_pct"):
            if rec.get(f) is not None:
                basis[f] = "estimate"
        rec["supplies_operations_pct"] = _residual(
            {**rec, "exec_comp_pct": rec.get("exec_comp_pct") or 0.0,
             "shareholder_extraction_pct": rec.get("shareholder_extraction_pct") or 0.0},
            ["clinical_care_wages_pct", "admin_overhead_pct", "exec_comp_pct", "shareholder_extraction_pct"],
        )
        basis["supplies_operations_pct"] = "residual"

    return _finish(rec, basis, withheld)


def _finish(rec: Dict[str, Any], basis: Dict[str, str], withheld: List[Dict[str, Any]]) -> Dict[str, Any]:
    rec["split_basis"] = basis
    # Public output names the withheld fields but never their values.
    rec["withheld_claims"] = [{"field": w["field"], "reason": w["reason"]} for w in withheld]
    rec["_withheld"] = withheld  # internal: values go to the verification queue only
    rec["rating_type"] = RATING_TYPE
    return rec


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
    "load_financials", "has_source",
]


if __name__ == "__main__":
    from pipeline.top2000_brands import generate_top_2000_brands
    from pipeline.healthcare_2000 import generate_healthcare_2000

    n = write_verification_queue({"brands": generate_top_2000_brands(), "healthcare": generate_healthcare_2000()})
    print(f"Wrote {n} withheld claims to {QUEUE_PATH}")
