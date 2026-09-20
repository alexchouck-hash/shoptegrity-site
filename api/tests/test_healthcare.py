import pytest
from fastapi.testclient import TestClient
from api.app.main import app
from api.app.db.session import SessionLocal
from api.app.models.core import HealthcareIntegrity


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_healthcare_database_count():
    """Verify that the database contains exactly 2,000 healthcare entities."""
    with SessionLocal() as db:
        count = db.query(HealthcareIntegrity).count()
        assert count == 2000, f"Expected 2000 healthcare entities, got {count}"


def test_healthcare_category_distribution():
    """Verify balanced distribution across insurance, hospital chains, corporate/PE clinics, and local clinics."""
    with SessionLocal() as db:
        insurers = db.query(HealthcareIntegrity).filter(HealthcareIntegrity.entity_type == "health_insurance").count()
        hospitals = db.query(HealthcareIntegrity).filter(HealthcareIntegrity.entity_type == "hospital_chain").count()
        corp_clinics = db.query(HealthcareIntegrity).filter(HealthcareIntegrity.entity_type == "corporate_clinic").count()
        local_clinics = db.query(HealthcareIntegrity).filter(HealthcareIntegrity.entity_type == "local_clinic").count()

        assert insurers == 350, f"Expected 350 insurers, got {insurers}"
        assert hospitals == 450, f"Expected 450 hospitals, got {hospitals}"
        assert corp_clinics == 600, f"Expected 600 corporate/PE clinics, got {corp_clinics}"
        assert local_clinics == 600, f"Expected 600 local clinics/offices, got {local_clinics}"


def test_healthcare_api_database_filtering(client):
    """Test REST API querying, searching, and filtering across the 2,000 entities."""
    # 1. Base database query
    resp = client.get("/v1/healthcare/database")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2000
    assert len(data["entities"]) == 50

    # 2. Filter by sector
    resp_ins = client.get("/v1/healthcare/database?entity_type=health_insurance&limit=10")
    assert resp_ins.status_code == 200
    assert resp_ins.json()["total"] == 350

    resp_local = client.get("/v1/healthcare/database?entity_type=local_clinic&limit=10")
    assert resp_local.status_code == 200
    assert resp_local.json()["total"] == 600

    # 3. Search query
    resp_search = client.get("/v1/healthcare/database?q=UnitedHealthcare")
    assert resp_search.status_code == 200
    search_data = resp_search.json()
    assert search_data["total"] >= 1
    assert any("UnitedHealthcare" in e["name"] for e in search_data["entities"])

    # 4. Filter by PE Rollup
    resp_pe = client.get("/v1/healthcare/database?is_pe_rollup=true")
    assert resp_pe.status_code == 200
    pe_data = resp_pe.json()
    assert pe_data["total"] > 0
    assert all(e["is_pe_rollup"] is True for e in pe_data["entities"])

    # 5. Filter by Tier 1 (Owner-Operated Local Doctors & Dentists)
    resp_t1 = client.get("/v1/healthcare/database?tier=1")
    assert resp_t1.status_code == 200
    t1_data = resp_t1.json()
    assert t1_data["total"] > 0
    assert all(e["ownership_tier"] == 1 for e in t1_data["entities"])


def test_healthcare_api_compare(client):
    """Test side-by-side comparison endpoint for 2 to 4 entities."""
    # Compare UnitedHealthcare vs Plum Health Direct Primary Care
    slugs = "unitedhealthcare-optum,plum-health-direct-primary-care"
    resp = client.get(f"/v1/healthcare/compare?slugs={slugs}")
    assert resp.status_code == 200
    comp = resp.json()

    assert comp["compared_count"] == 2
    assert len(comp["entities"]) == 2
    assert "metrics_matrix" in comp
    assert "names" in comp["metrics_matrix"]
    assert len(comp["metrics_matrix"]["names"]) == 2

    # Verify integrity winner
    winner = comp["highest_integrity_entity"]
    assert "Plum Health" in winner["name"]
    assert winner["tier"] == 1
    assert winner["score"] > 90

    # Error handling for invalid slug
    resp_404 = client.get("/v1/healthcare/compare?slugs=non-existent-entity-xyz")
    assert resp_404.status_code == 404


def test_healthcare_api_stats(client):
    """Test stats aggregation endpoint."""
    resp = client.get("/v1/healthcare/stats")
    assert resp.status_code == 200
    stats = resp.json()

    assert stats["total_entities"] == 2000
    assert stats["by_entity_type"]["health_insurance"] == 350
    assert stats["by_entity_type"]["hospital_chain"] == 450
    assert stats["by_entity_type"]["corporate_clinic"] == 600
    assert stats["by_entity_type"]["local_clinic"] == 600
    assert stats["pe_rollups_count"] > 0
    assert "averages" in stats
    assert stats["averages"]["clinical_care_wages_pct"] > 0


def test_healthcare_entity_detail(client):
    """Test individual entity scorecard detail endpoint."""
    resp = client.get("/v1/healthcare/unitedhealthcare-optum")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["name"] == "UnitedHealthcare (Optum)"
    assert detail["ownership_tier"] == 6
    assert detail["grade"] == "F"
    assert detail["clinical_care_wages_pct"] == 58.5
    assert detail["shareholder_extraction_pct"] == 11.2
    assert detail["swap_name"] is not None


def test_healthcare_web_view(client):
    """Test that the /healthcare HTML view renders successfully with 2,000 comparison features."""
    resp = client.get("/healthcare")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Healthcare Comparisons (2,000)" in resp.text
    assert "Side-by-Side Healthcare Comparison" in resp.text
