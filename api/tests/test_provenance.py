"""Publication gate: synthetic records never ship, unsourced claims are withheld."""

import json
import re
from pathlib import Path

import pytest

from pipeline.provenance import (
    gate_brand, gate_healthcare, assert_no_synthetic, public_record, write_verification_queue,
)
from pipeline.sec_financials import extract_financials
from pipeline.top2000_brands import generate_top_2000_brands, export_top2000_json
from pipeline.healthcare_2000 import generate_healthcare_2000

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


def test_sec_extraction_uses_full_year_values():
    fin = extract_financials("1", FAKE_FACTS)
    assert fin["fiscal_year_end"] == "2024-12-31"
    assert fin["figures"]["buybacks"]["value"] == 20_000_000
    assert fin["figures"]["revenue"]["url"] == "https://www.sec.gov/Archives/edgar/data/1/000000000025000001/"


def test_gate_replaces_hand_typed_financials_and_withholds_unsourced_claims():
    financials = {"0000000001": extract_financials("1", FAKE_FACTS)}
    rec = gate_brand(_brand(), financials)

    # Payout share derived from the filing: (30M + 20M) / 1B = 5.0%, not the hand-typed 25%.
    assert rec["shareholder_extraction_pct"] == 5.0
    assert rec["split_basis"]["shareholder_extraction_pct"] == "sec_filing"
    assert rec["split_basis"]["worker_wages_pct"] == "estimate"
    assert rec["sec_receipt_details"]["total_shareholder_payout_usd"] == "$50.00 Million"

    for field in ["osha_violations_count", "nlrb_complaints_count", "labor_summary", "waste_summary", "exec_comp_pct"]:
        assert rec[field] is None
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


def test_hand_labelled_sec_record_without_filing_is_downgraded():
    rec = gate_brand(_brand(), {})
    assert rec["data_provenance"] == "unverified"
    assert rec["sec_receipt_details"] is None
    assert rec["shareholder_extraction_pct"] is None


def test_coop_has_structural_zero_payout():
    rec = gate_brand(_brand(ownership_type="cooperative", parent_company="Example Co-op", shareholder_extraction_pct=0.0), {})
    assert rec["shareholder_extraction_pct"] == 0.0
    assert rec["split_basis"]["shareholder_extraction_pct"] == "ownership_structure"


def test_modeled_healthcare_numbers_about_real_company_are_withheld():
    rec = gate_healthcare({
        "name": "Some Dental Chain", "parent_organization": "Some PE Firm", "ownership_type": "private_equity",
        "clinical_care_wages_pct": 40.0, "admin_overhead_pct": 20.0, "exec_comp_pct": 3.0,
        "shareholder_extraction_pct": 20.0, "supplies_operations_pct": 17.0, "claims_denial_rate_pct": 0.0,
        "is_pe_rollup": True, "pe_firm_name": "Some PE Firm", "data_provenance": "industry_benchmark_model",
    }, {})
    assert rec["data_provenance"] == "ownership_profile"
    assert all(rec[f] is None for f in ["clinical_care_wages_pct", "shareholder_extraction_pct", "pe_firm_name", "is_pe_rollup"])


def test_assert_no_synthetic_blocks_generated_records():
    with pytest.raises(ValueError):
        assert_no_synthetic([{"name": "Apex Foods #123", "data_provenance": "unverified"}], "brands")
    with pytest.raises(ValueError):
        assert_no_synthetic([{"name": "Real Name", "data_provenance": "industry_benchmark_model"}], "brands")


def test_real_pipelines_publish_no_synthetic_or_unsourced_facts():
    brands = generate_top_2000_brands()
    health = generate_healthcare_2000()
    assert not any(re.search(r"#\d+", b["name"]) for b in brands)
    for b in brands:
        for field in ["osha_violations_count", "nlrb_complaints_count", "labor_summary", "waste_summary"]:
            if field not in b["claim_sources"]:
                assert b[field] is None, f"{b['name']} publishes unsourced {field}"
        if b["sec_receipt_details"]:
            assert b["sec_receipt_details"]["filing_url"].startswith("https://www.sec.gov/Archives/")
    assert len(health) > 0


def test_exported_json_contains_no_withheld_values(tmp_path):
    out = tmp_path / "brands.json"
    export_top2000_json(output_path=str(out), retailers_path=str(tmp_path / "retailers.json"))
    data = json.loads(out.read_text(encoding="utf-8"))
    assert all("_withheld" not in b for b in data)
    walmart = next(b for b in data if b["name"] == "Walmart")
    assert walmart["osha_violations_count"] is None
    assert "Extensive history of wage suppression" not in out.read_text(encoding="utf-8")


def test_verification_queue_lists_withheld_values(tmp_path):
    path = tmp_path / "queue.csv"
    n = write_verification_queue({"brands": generate_top_2000_brands()}, path=path)
    assert n > 0
    text = path.read_text(encoding="utf-8")
    assert "osha_violations_count" in text
