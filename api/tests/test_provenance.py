"""Publication gate: synthetic rows are refused before any gate, every gated field is withheld
unless sourced, and ratings are published only when the rubric has every input."""

import json
import re
from pathlib import Path

import pytest

from pipeline import healthcare_2000, top2000_brands
from pipeline.provenance import (
    BRAND_CLAIM_FIELDS, HEALTH_CLAIM_FIELDS, RATING_FIELDS, RATING_TYPE, assert_no_synthetic,
    gate_brand, gate_healthcare, has_source, public_record, write_verification_queue,
)
from pipeline.sec_financials import extract_financials
from pipeline.top2000_brands import generate_top_2000_brands
from pipeline.healthcare_2000 import generate_healthcare_2000

MODELED = "industry_benchmark_model"
SOURCE = {"citation": "Example filing", "url": "https://www.sec.gov/Archives/edgar/data/1/000000000025000001/"}
RATING_FIELD_NAMES = {"composite_score", "grade", "labor_exploitation_rating", "sweatshop_risk", "waste_rating"}

FAKE_FACTS = {
    "entityName": "Example Corp",
    "facts": {"us-gaap": {
        "Revenues": {"units": {"USD": [
            {"start": "2024-01-01", "end": "2024-12-31", "val": 1_000_000_000, "accn": "0000000000-25-000001", "form": "10-K", "filed": "2025-02-01"},
        ]}},
        "NetIncomeLoss": {"units": {"USD": [
            {"start": "2024-01-01", "end": "2024-12-31", "val": 100_000_000, "accn": "0000000000-25-000001", "form": "10-K", "filed": "2025-02-01"},
        ]}},
        "PaymentsOfDividendsCommonStock": {"units": {"USD": [
            {"start": "2024-01-01", "end": "2024-12-31", "val": 30_000_000, "accn": "0000000000-25-000001", "form": "10-K", "filed": "2025-02-01"},
        ]}},
        "PaymentsForRepurchaseOfCommonStock": {"units": {"USD": [
            {"start": "2024-01-01", "end": "2024-12-31", "val": 20_000_000, "accn": "0000000000-25-000001", "form": "10-K", "filed": "2025-02-01"},
            # A quarterly value must be ignored.
            {"start": "2024-10-01", "end": "2024-12-31", "val": 999_000_000, "accn": "0000000000-25-000001", "form": "10-K", "filed": "2025-02-01"},
        ]}},
    }},
}


def _financials():
    return {"0000000001": extract_financials("1", FAKE_FACTS)}


def _brand(**overrides):
    base = {
        "name": "Example", "category": "Test", "parent_company": "Example Corp (Public: EX, CIK: 0000000001)",
        "ownership_type": "public", "composite_score": 30, "grade": "D",
        "worker_wages_pct": 20.0, "exec_comp_pct": 3.0, "shareholder_extraction_pct": 25.0,
        "marketing_ads_pct": 5.0, "cogs_supply_pct": 40.0, "retained_operations_pct": 7.0,
        "labor_exploitation_rating": "High Risk", "sweatshop_risk": "Low",
        "osha_violations_count": 312, "nlrb_complaints_count": 89, "living_wage_certified": False,
        "labor_summary": "An unsourced allegation.", "waste_rating": "Moderate", "packaging_type": "Plastic",
        "repairability_score": 3, "landfill_diverted_pct": 30.0, "waste_summary": "Unsourced.",
        "data_provenance": "verified_sec_filing", "sec_receipt_details": {"ceo_pay_ratio": 999},
    }
    base.update(overrides)
    return base


def _healthcare(**overrides):
    base = {
        "name": "Some Dental Chain", "parent_organization": "Some PE Firm", "ownership_type": "private_equity",
        "ownership_tier": 5, "entity_type": "dental", "sub_category": "DSO Dental",
        "clinical_care_wages_pct": 40.0, "admin_overhead_pct": 20.0, "exec_comp_pct": 3.0,
        "shareholder_extraction_pct": 20.0, "supplies_operations_pct": 17.0, "claims_denial_rate_pct": 0.0,
        "is_pe_rollup": True, "pe_firm_name": "Some PE Firm", "composite_score": 28, "grade": "D",
        "source_citation": "Unsourced", "filing_url": "https://example.com/unsourced",
        "data_provenance": "unverified",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# SEC extraction and receipts
# ---------------------------------------------------------------------------

def test_sec_extraction_uses_full_year_values():
    fin = extract_financials("1", FAKE_FACTS)
    assert fin["fiscal_year_end"] == "2024-12-31"
    assert fin["figures"]["buybacks"]["value"] == 20_000_000
    assert fin["figures"]["revenue"]["url"] == "https://www.sec.gov/Archives/edgar/data/1/000000000025000001/"


def test_receipt_backs_payout_and_parent_but_not_wages():
    rec = gate_brand(_brand(), _financials())
    # Payout share from the filing: (30M + 20M) / 1B = 5.0%, not the hand-typed 25%.
    assert rec["shareholder_extraction_pct"] == 5.0
    assert rec["split_basis"]["shareholder_extraction_pct"] == "sec_filing"
    assert rec["parent_company"] == "Example Corp (Public: EX, CIK: 0000000001)"
    assert rec["sec_url"] == rec["sec_receipt_details"]["filing_url"]
    assert rec["data_provenance"] == "verified_sec_filing"
    # A receipt has no wage figures, so the hand-typed wage split is withheld.
    assert rec["worker_wages_pct"] is None
    assert {"worker_wages_pct", "marketing_ads_pct", "cogs_supply_pct"} <= {w["field"] for w in rec["withheld_claims"]}


def test_unsourced_brand_claims_are_withheld_and_never_printed():
    rec = gate_brand(_brand(), _financials())
    for field in ["osha_violations_count", "nlrb_complaints_count", "labor_summary", "waste_summary", "exec_comp_pct"]:
        assert rec[field] is None, field
    withheld_fields = {w["field"] for w in rec["withheld_claims"]}
    assert {"osha_violations_count", "labor_summary", "sec_receipt_details.ceo_pay_ratio"} <= withheld_fields

    public = public_record(rec)
    assert "_withheld" not in public
    assert "312" not in json.dumps(public)


def test_sourced_claim_survives_the_gate():
    rec = gate_brand(_brand(claim_sources={
        "osha_violations_count": {"citation": "OSHA establishment search", "url": "https://www.osha.gov/ords/imis/establishment.html"},
    }), {})
    assert rec["osha_violations_count"] == 312
    assert rec["nlrb_complaints_count"] is None


def test_citation_without_url_does_not_count():
    rec = gate_brand(_brand(claim_sources={"osha_violations_count": {"citation": "trust me", "url": ""}}), {})
    assert rec["osha_violations_count"] is None


def test_verified_sec_label_without_a_receipt_is_downgraded():
    rec = gate_brand(_brand(sec_url="https://www.sec.gov/edgar/browse/?CIK=0000000001"), {})
    assert rec["data_provenance"] == "unverified"
    assert rec["sec_receipt_details"] is None
    assert rec["sec_url"] is None
    assert rec["shareholder_extraction_pct"] is None
    assert rec["parent_company"] is None


# ---------------------------------------------------------------------------
# Splits and residuals
# ---------------------------------------------------------------------------

def test_structural_zero_payout_needs_a_sourced_ownership_type():
    unsourced = gate_brand(_brand(ownership_type="cooperative", parent_company="Example Co-op", shareholder_extraction_pct=0.0), {})
    assert unsourced["ownership_type"] is None
    assert unsourced["shareholder_extraction_pct"] is None

    sourced = gate_brand(_brand(
        ownership_type="cooperative", parent_company="Example Co-op", shareholder_extraction_pct=0.0,
        claim_sources={"ownership_type": SOURCE},
    ), {})
    assert sourced["ownership_type"] == "cooperative"
    assert sourced["shareholder_extraction_pct"] == 0.0
    assert sourced["split_basis"]["shareholder_extraction_pct"] == "ownership_structure"


@pytest.mark.parametrize("field", ["worker_wages_pct", "marketing_ads_pct", "cogs_supply_pct"])
def test_wage_marketing_and_cogs_splits_need_a_per_claim_source(field):
    bare = gate_brand(_brand(), {})
    assert bare[field] is None
    assert field in {w["field"] for w in bare["withheld_claims"]}

    cited = gate_brand(_brand(claim_sources={field: SOURCE}), {})
    assert cited[field] is not None
    assert cited["split_basis"][field] == "claim_source"


def test_residual_is_computed_only_from_published_inputs():
    all_cited = {f: SOURCE for f in ["worker_wages_pct", "marketing_ads_pct", "cogs_supply_pct",
                                      "shareholder_extraction_pct", "exec_comp_pct"]}
    rec = gate_brand(_brand(claim_sources=all_cited), {})
    # 100 - (20 + 3 + 25 + 5 + 40) = 7.0, from cited values only.
    assert rec["retained_operations_pct"] == 7.0
    assert rec["split_basis"]["retained_operations_pct"] == "residual"

    missing_exec = {k: v for k, v in all_cited.items() if k != "exec_comp_pct"}
    rec = gate_brand(_brand(claim_sources=missing_exec), {})
    assert rec["retained_operations_pct"] is None


# ---------------------------------------------------------------------------
# Synthetic rows
# ---------------------------------------------------------------------------

def test_assert_no_synthetic_blocks_generated_records():
    with pytest.raises(ValueError):
        assert_no_synthetic([{"name": "Apex Foods #123", "data_provenance": "unverified"}], "brands")
    with pytest.raises(ValueError):
        assert_no_synthetic([{"name": "Real Name", "data_provenance": MODELED}], "brands")


def test_modeled_rows_are_refused_not_relabelled():
    with pytest.raises(ValueError):
        gate_brand(_brand(data_provenance=MODELED), {})
    with pytest.raises(ValueError):
        gate_healthcare(_healthcare(data_provenance=MODELED), {})


def test_modeled_row_with_a_receipt_still_refused_so_no_split_can_take_a_filed_label():
    with pytest.raises(ValueError):
        gate_brand(_brand(data_provenance=MODELED), _financials())


def test_synthetic_check_runs_on_raw_brand_output_before_the_gate(monkeypatch):
    modeled = dict(top2000_brands.VERIFIED_CORPORATIONS[0], data_provenance=MODELED)
    calls = []
    monkeypatch.setattr(top2000_brands, "VERIFIED_CORPORATIONS", [modeled])
    monkeypatch.setattr(top2000_brands, "gate_brand", lambda *a, **k: calls.append(a) or {})
    with pytest.raises(ValueError):
        generate_top_2000_brands()
    assert calls == []  # the gate never saw the modeled row


def test_synthetic_check_runs_on_raw_healthcare_output_before_the_gate(monkeypatch):
    modeled = dict(healthcare_2000.VERIFIED_HEALTHCARE_ENTITIES[0], data_provenance=MODELED)
    calls = []
    monkeypatch.setattr(healthcare_2000, "VERIFIED_HEALTHCARE_ENTITIES", [modeled])
    monkeypatch.setattr(healthcare_2000, "gate_healthcare", lambda *a, **k: calls.append(a) or {})
    with pytest.raises(ValueError):
        generate_healthcare_2000()
    assert calls == []


def test_generated_catalogs_contain_no_modeled_or_removed_entities():
    brands = generate_top_2000_brands()
    health = generate_healthcare_2000()
    assert all(r["data_provenance"] != MODELED for r in brands + health)
    assert not any(re.search(r"#\d+", r["name"]) for r in brands + health)
    removed_brands = {"Aspen Dental", "Heartland Dental", "ClearChoice Dental Implant Centers"}
    assert not removed_brands & {r["name"] for r in brands}
    removed_health = {"Heartland Dental (1,700+ Rollup Offices)", "Aspen Dental (TAG - The Aspen Group)",
                      "Schweiger Dermatology Group", "Athletico Physical Therapy"}
    assert not removed_health & {r["name"] for r in health}


# ---------------------------------------------------------------------------
# Ratings
# ---------------------------------------------------------------------------

def test_generator_source_has_no_hand_typed_score_literals():
    for module in (top2000_brands, healthcare_2000):
        text = Path(module.__file__).read_text(encoding="utf-8")
        assert not re.search(r'"composite_score":\s*\d', text), module.__name__
        assert not re.search(r'"grade":\s*"', text), module.__name__
        assert not re.search(r'"score":\s*"', text), module.__name__
        assert not re.search(r'"(labor_exploitation_rating|sweatshop_risk|waste_rating)":\s*"', text), module.__name__


def test_every_rating_is_withheld_and_listed_unless_the_rubric_has_every_input():
    for rec in generate_top_2000_brands():
        assert rec["composite_score"] is None and rec["grade"] is None
        assert rec["labor_exploitation_rating"] is None and rec["sweatshop_risk"] is None
        assert rec["waste_rating"] is None and rec["rating_type"] is None
        listed = {w["field"] for w in rec["withheld_claims"]}
        assert RATING_FIELD_NAMES <= listed, rec["name"]
    for rec in generate_healthcare_2000():
        assert rec["composite_score"] is None and rec["grade"] is None
        assert {"composite_score", "grade"} <= {w["field"] for w in rec["withheld_claims"]}


def test_composite_comes_from_the_rubric_and_needs_every_input():
    cited = {f: SOURCE for f in [
        "ownership_type", "shareholder_extraction_pct", "sec_receipt_details.ceo_pay_ratio", "osha_violations_count",
        "nlrb_complaints_count", "living_wage_certified", "landfill_diverted_pct", "waste_summary", "locality_tier",
    ]}
    rec = gate_brand(_brand(claim_sources=cited, locality_tier="national_public", living_wage_certified=True), {})
    assert isinstance(rec["composite_score"], float)
    assert 0.0 <= rec["composite_score"] <= 100.0
    assert rec["rating_type"] == RATING_TYPE
    assert rec["grade"] is None  # no band table exists in code
    assert rec["labor_exploitation_rating"] is None

    without_locality = {k: v for k, v in cited.items() if k != "locality_tier"}
    rec = gate_brand(_brand(claim_sources=without_locality, living_wage_certified=True), {})
    assert rec["composite_score"] is None
    assert rec["rating_type"] is None
    reasons = [w["reason"] for w in rec["withheld_claims"] if w["field"] == "composite_score"]
    assert reasons and "locality_tier" in reasons[0]


def test_champion_status_needs_a_published_composite_of_90_or_more():
    rec = gate_brand(_brand(is_champion=True), {})
    assert rec["is_champion"] is False
    assert "is_champion" in {w["field"] for w in rec["withheld_claims"]}


def test_swap_scores_are_never_published_and_swap_text_is_gated():
    swap = {"name": "Example Co-op", "tier": "best", "score": "98/100 (Grade A+)",
            "price_level": "Save $30 a year", "experience": "Certified B Corp", "rationale": "Keeps wealth local"}

    # An uncited ranked option is withheld as a whole: no name, score, or text is published
    rec = gate_brand(_brand(better_swap=dict(swap), swap_name="Example Co-op", swap_rationale="Unsourced."), {})
    assert rec["better_swap"] is None
    assert rec["swap_name"] is None and rec["swap_rationale"] is None
    assert "better_swap.name" in {w["field"] for w in rec["withheld_claims"]}

    # A cited option name may show, but the score and every uncited text field still do not
    cited = gate_brand(_brand(better_swap=dict(swap), claim_sources={"better_swap.name": SOURCE}), {})
    better = cited["better_swap"]
    assert better["name"] == "Example Co-op" and better["tier"] == "best"
    assert better["score"] is None
    assert better["experience"] is None and better["rationale"] is None
    assert better["price_level"] is None  # figures in price text are a claim
    assert "better_swap.score" in {w["field"] for w in cited["withheld_claims"]}

    sourced = gate_brand(_brand(
        better_swap={"name": "X", "tier": "best", "price_level": "Secondhand savings"},
        claim_sources={"better_swap.name": SOURCE, "better_swap.price_level": SOURCE},
    ), {})
    assert sourced["better_swap"]["price_level"] == "Secondhand savings"


def test_parent_entity_and_text_claims_are_gated():
    rec = gate_brand(_brand(parent_entity={"name": "Example Corp", "ownership_type": "public"},
                            champion_highlight="Named company claim."), {})
    assert rec["parent_entity"] is None
    assert rec["champion_highlight"] is None
    assert {"parent_entity", "champion_highlight"} <= {w["field"] for w in rec["withheld_claims"]}


# ---------------------------------------------------------------------------
# Data-provenance labels
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label", ["certified_audit", "state_insurance_filing", "cms_cost_report"])
def test_labels_that_assert_verification_need_a_per_claim_url(label):
    bare = gate_brand(_brand(data_provenance=label, sec_receipt_details=None), {})
    assert bare["data_provenance"] == "unverified"

    cited = gate_brand(_brand(data_provenance=label, sec_receipt_details=None, claim_sources={"labor_summary": SOURCE}), {})
    assert cited["data_provenance"] == label


def test_healthcare_label_needs_a_per_claim_url():
    assert gate_healthcare(_healthcare(data_provenance="cms_cost_report"), {})["data_provenance"] == "unverified"
    kept = gate_healthcare(_healthcare(data_provenance="cms_cost_report", claim_sources={"summary_notes": SOURCE}), {})
    assert kept["data_provenance"] == "cms_cost_report"


# ---------------------------------------------------------------------------
# Healthcare fields
# ---------------------------------------------------------------------------

def test_healthcare_ownership_and_splits_are_withheld_without_sources():
    rec = gate_healthcare(_healthcare(), {})
    for field in ["parent_organization", "ownership_type", "ownership_tier", "shareholder_extraction_pct",
                  "exec_comp_pct", "clinical_care_wages_pct", "admin_overhead_pct", "supplies_operations_pct",
                  "is_pe_rollup", "pe_firm_name", "claims_denial_rate_pct", "source_citation", "filing_url",
                  "composite_score", "grade"]:
        assert rec[field] is None, field
    assert rec["data_provenance"] == "unverified"


def test_healthcare_residual_and_structural_zero_follow_sourced_inputs():
    cited = {f: SOURCE for f in ["parent_organization", "ownership_type", "ownership_tier",
                                 "clinical_care_wages_pct", "admin_overhead_pct", "exec_comp_pct"]}
    rec = gate_healthcare(_healthcare(claim_sources=cited), {})
    assert rec["clinical_care_wages_pct"] == 40.0
    assert rec["exec_comp_pct"] == 3.0
    assert rec["shareholder_extraction_pct"] is None  # private equity payout needs a filing or a source
    assert rec["supplies_operations_pct"] is None

    rec = gate_healthcare(_healthcare(
        ownership_type="physician_owned", shareholder_extraction_pct=0.0,
        claim_sources={"ownership_type": SOURCE, "clinical_care_wages_pct": SOURCE,
                       "admin_overhead_pct": SOURCE, "exec_comp_pct": SOURCE},
    ), {})
    assert rec["shareholder_extraction_pct"] == 0.0
    assert rec["split_basis"]["shareholder_extraction_pct"] == "ownership_structure"
    assert rec["supplies_operations_pct"] == round(100.0 - (40.0 + 20.0 + 3.0 + 0.0), 1)


def test_healthcare_gated_text_fields_are_withheld():
    rec = gate_healthcare(_healthcare(swap_name="Example Co-op", swap_rationale="Named claim.",
                                      summary_notes="Named claim.", regulatory_citations=["Settlement X"]), {})
    for field in ["swap_name", "swap_rationale", "summary_notes"]:
        assert rec[field] is None
    assert rec["regulatory_citations"] == []
    listed = {w["field"] for w in rec["withheld_claims"]}
    assert {"swap_name", "swap_rationale", "summary_notes", "regulatory_citations"} <= listed


def test_gated_field_lists_cover_the_audit_classes():
    assert {"parent_entity", "swap_name", "swap_rationale", "swap_highlight", "champion_highlight"} <= set(BRAND_CLAIM_FIELDS)
    assert {"is_pe_rollup", "pe_firm_name", "swap_name", "swap_rationale", "summary_notes"} <= set(HEALTH_CLAIM_FIELDS)
    assert RATING_FIELD_NAMES <= set(RATING_FIELDS)
    assert has_source({"x": SOURCE}, "x") and not has_source({"x": {"citation": "c"}}, "x")


# ---------------------------------------------------------------------------
# Published output
# ---------------------------------------------------------------------------

def test_public_catalog_drops_internal_keys_and_withheld_values():
    brands = [public_record(b) for b in generate_top_2000_brands()]
    assert all("_withheld" not in b for b in brands)
    assert all(set(w) == {"field", "reason"} for b in brands for w in b["withheld_claims"])
    dumped = json.dumps(brands)
    # Walmart's hand-typed labor summary is withheld (no per-claim source).
    assert "Extensive history of wage suppression" not in dumped


def test_real_pipelines_publish_only_sourced_or_filed_facts():
    for rec in generate_top_2000_brands():
        src = rec["claim_sources"]
        receipt = rec["sec_receipt_details"]
        for field in ["osha_violations_count", "nlrb_complaints_count", "living_wage_certified", "labor_summary",
                      "waste_summary", "packaging_type", "repairability_score", "landfill_diverted_pct",
                      "swap_name", "swap_rationale", "worker_wages_pct", "marketing_ads_pct", "cogs_supply_pct"]:
            if rec[field] is not None:
                assert has_source(src, field), f"{rec['name']} publishes unsourced {field}"
        if rec["parent_company"] is not None:
            assert receipt or has_source(src, "parent_company"), rec["name"]
        if receipt:
            assert receipt["filing_url"].startswith("https://www.sec.gov/Archives/")
        if rec["data_provenance"] == "verified_sec_filing":
            assert receipt is not None, rec["name"]
        if rec["composite_score"] is not None:
            assert has_source(src, "locality_tier"), rec["name"]

    for rec in generate_healthcare_2000():
        src = rec["claim_sources"]
        receipt = rec["sec_receipt_details"]
        for field in HEALTH_CLAIM_FIELDS:
            if rec.get(field) not in (None, [], False):
                assert has_source(src, field), f"{rec['name']} publishes unsourced {field}"
        if rec["data_provenance"] == "verified_sec_filing":
            assert receipt is not None, rec["name"]


def test_verification_queue_lists_withheld_ratings(tmp_path):
    path = tmp_path / "queue.csv"
    n = write_verification_queue({"brands": generate_top_2000_brands()}, path=path)
    assert n > 0
    text = path.read_text(encoding="utf-8")
    assert "composite_score" in text
    assert "labor_exploitation_rating" in text
