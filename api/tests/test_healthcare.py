import re

import pytest
from fastapi.testclient import TestClient
from api.app.main import app
from api.app.db.session import SessionLocal
from api.app.models.core import HealthcareIntegrity
from pipeline.healthcare_2000 import VERIFIED_HEALTHCARE_ENTITIES


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_healthcare_database_contains_only_curated_entities():
    """No generated filler: the table holds exactly the hand-curated records."""
    with SessionLocal() as db:
        names = [r.name for r in db.query(HealthcareIntegrity).all()]
    assert len(names) == len(VERIFIED_HEALTHCARE_ENTITIES)
    assert not any(re.search(r"#\d+", n) for n in names)
    with SessionLocal() as db:
        assert db.query(HealthcareIntegrity).filter(HealthcareIntegrity.data_provenance == "industry_benchmark_model").count() == 0


def test_healthcare_category_coverage():
    """Every entity type is still represented."""
    with SessionLocal() as db:
        for entity_type in ["health_insurance", "hospital_chain", "corporate_clinic", "local_clinic"]:
            assert db.query(HealthcareIntegrity).filter(HealthcareIntegrity.entity_type == entity_type).count() > 0


def test_healthcare_api_database_filtering(client):
    """Test REST API querying, searching, and filtering."""
    resp = client.get("/v1/healthcare/database")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == len(VERIFIED_HEALTHCARE_ENTITIES)

    resp_ins = client.get("/v1/healthcare/database?entity_type=health_insurance&limit=10")
    assert resp_ins.status_code == 200
    assert all(e["entity_type"] == "health_insurance" for e in resp_ins.json()["entities"])

    resp_search = client.get("/v1/healthcare/database?q=UnitedHealthcare")
    assert resp_search.status_code == 200
    search_data = resp_search.json()
    assert search_data["total"] >= 1
    assert any("UnitedHealthcare" in e["name"] for e in search_data["entities"])

    resp_t1 = client.get("/v1/healthcare/database?tier=1")
    assert resp_t1.status_code == 200
    t1_data = resp_t1.json()
    assert t1_data["total"] > 0
    assert all(e["ownership_tier"] == 1 for e in t1_data["entities"])


def test_unsourced_claims_are_withheld(client):
    """Denial rates, markups, PE sponsors etc. are null unless the record cites a source."""
    entities = client.get("/v1/healthcare/database?limit=1000").json()["entities"]
    for e in entities:
        sources = e["claim_sources"]
        for field in ["claims_denial_rate_pct", "charge_to_cost_ratio", "medical_loss_ratio_pct",
                      "charity_care_pct", "pe_firm_name", "is_pe_rollup", "summary_notes"]:
            if field not in sources:
                assert e[field] is None, f"{e['name']}: unsourced {field} published"
        if "regulatory_citations" not in sources:
            assert e["regulatory_citations"] == []
        # Public output names withheld fields but never their values.
        assert all(set(w) == {"field", "reason"} for w in e["withheld_claims"])


def test_healthcare_api_compare(client):
    slugs = "unitedhealthcare-optum,plum-health-direct-primary-care"
    resp = client.get(f"/v1/healthcare/compare?slugs={slugs}")
    assert resp.status_code == 200
    comp = resp.json()

    assert comp["compared_count"] == 2
    assert len(comp["metrics_matrix"]["names"]) == 2
    winner = comp["highest_integrity_entity"]
    assert "Plum Health" in winner["name"]
    assert winner["tier"] == 1

    resp_404 = client.get("/v1/healthcare/compare?slugs=non-existent-entity-xyz")
    assert resp_404.status_code == 404


def test_healthcare_api_stats(client):
    resp = client.get("/v1/healthcare/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total_entities"] == len(VERIFIED_HEALTHCARE_ENTITIES)
    assert "averages" in stats


def test_healthcare_entity_detail_uses_sec_figures(client):
    """UnitedHealth's shareholder payout share comes from its 10-K, not a hand-typed value."""
    resp = client.get("/v1/healthcare/unitedhealthcare-optum")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["name"] == "UnitedHealthcare (Optum)"
    assert detail["data_provenance"] == "verified_sec_filing"
    receipt = detail["sec_receipt_details"]
    assert receipt and receipt["filing_url"].startswith("https://www.sec.gov/Archives/")
    assert detail["shareholder_extraction_pct"] == round(receipt["shareholder_payout_pct_of_revenue"], 1)
    assert detail["split_basis"]["shareholder_extraction_pct"] == "sec_filing"
    assert detail["split_basis"]["clinical_care_wages_pct"] == "estimate"


def test_healthcare_web_view(client):
    resp = client.get("/healthcare")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Healthcare Comparisons" in resp.text
    assert "Side-by-Side Healthcare Comparison" in resp.text
