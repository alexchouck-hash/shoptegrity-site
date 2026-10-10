import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.app.main import app
from api.app.db.session import SessionLocal, get_db
from api.app.models.core import Base, HealthcareIntegrity
from api.app.routers.healthcare import WITHHELD_TEXT, serialize_entity
from pipeline.healthcare_2000 import VERIFIED_HEALTHCARE_ENTITIES

# Fields that need a cited source; SEC-backed fields may instead cite the entity's 10-K receipt.
SEC_BACKED = {"parent_organization", "ownership_type", "ownership_tier", "shareholder_extraction_pct", "exec_comp_pct"}
CITED_ONLY = [
    "medical_loss_ratio_pct", "claims_denial_rate_pct", "charge_to_cost_ratio", "charity_care_pct",
    "pe_firm_name", "is_pe_rollup", "summary_notes", "clinical_care_wages_pct", "admin_overhead_pct",
    "supplies_operations_pct", "swap_name", "swap_rationale",
]
# Wording that the owner policy removed from the page (accusations, unsourced counts and absence claims).
FORBIDDEN_ON_PAGE = [
    "Disguised", "disguised", "Severe Denial", "PE Rollup / Chain", "PE Extraction",
    "no outside shareholders", "Medicare cost", "sponsor not yet sourced", "Not PE-owned",
    "Highest Integrity", "Wall St Insurer", "(350)", "(450)", "(600)",
]
CITED_SOURCES = {
    "medical_loss_ratio_pct": {"url": "https://example.gov/mlr-filing", "citation": "Example MLR filing"},
    "claims_denial_rate_pct": {"url": "https://example.gov/denials", "citation": "Example denial report"},
    "pe_firm_name": {"url": "https://example.gov/sponsor", "citation": "Example sponsor disclosure"},
    "is_pe_rollup": {"url": "https://example.gov/sponsor", "citation": "Example sponsor disclosure"},
    "composite_score": {"url": "https://example.gov/rubric-inputs", "citation": "Example inputs"},
    "swap_name": {"url": "https://example.gov/swap", "citation": "Example swap source"},
    "swap_rationale": {"url": "https://example.gov/swap", "citation": "Example swap source"},
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _has_cite(entity, field):
    src = (entity["claim_sources"] or {}).get(field)
    if isinstance(src, dict) and str(src.get("url", "")).startswith(("http://", "https://")) and str(src.get("citation", "")).strip():
        return True
    if field in SEC_BACKED:
        url = (entity["sec_receipt_details"] or {}).get("filing_url") or ""
        return url.startswith(("http://", "https://"))
    return False


def _record(**overrides):
    """A transient HealthcareIntegrity row for serializer and template tests (not the shared test DB)."""
    values = dict(
        id="test-cited-clinic",
        name="Example Clinic Group",
        slug="example-clinic-group",
        entity_type="corporate_clinic",
        sub_category="Urgent Care",
        parent_organization="Example Holdings Inc.",
        ownership_type="private_equity",
        ownership_tier=5,
        composite_score=40,
        grade="D",
        clinical_care_wages_pct=61.0,
        admin_overhead_pct=20.0,
        exec_comp_pct=None,
        shareholder_extraction_pct=None,
        supplies_operations_pct=None,
        medical_loss_ratio_pct=83.5,
        claims_denial_rate_pct=12.5,
        charge_to_cost_ratio=2.1,
        charity_care_pct=None,
        is_pe_rollup=True,
        pe_firm_name="Sponsor Capital LP",
        regulatory_citations=["Consent order"],
        swap_name="Local Direct Primary Care",
        swap_slug="local-direct-primary-care",
        swap_type="direct_primary_care",
        swap_rationale="Flat-fee physician practice.",
        location_scope="Local",
        city="Austin",
        state="TX",
        data_provenance="unverified",
        source_citation=None,
        filing_url=None,
        summary_notes=None,
        sec_receipt_details=None,
        claim_sources={},
        withheld_claims=[],
        split_basis={},
        rating_type=None,
    )
    values.update(overrides)
    return HealthcareIntegrity(**values)


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

    # Tier and PE filters match cited values only, so their totals equal the published values.
    everyone = client.get("/v1/healthcare/database?limit=1000").json()["entities"]
    resp_t1 = client.get("/v1/healthcare/database?tier=1&limit=1000").json()
    assert resp_t1["total"] == sum(1 for e in everyone if e["ownership_tier"] == 1)
    assert all(e["ownership_tier"] == 1 and _has_cite(e, "ownership_tier") for e in resp_t1["entities"])

    resp_pe = client.get("/v1/healthcare/database?is_pe_rollup=true&limit=1000").json()
    assert resp_pe["total"] == sum(1 for e in everyone if e["is_pe_rollup"] is True)


def test_unsourced_claims_are_withheld(client):
    """Every claim, rating, swap and ownership value is null unless the record cites a source for it."""
    entities = client.get("/v1/healthcare/database?limit=1000").json()["entities"]
    for e in entities:
        for field in CITED_ONLY + sorted(SEC_BACKED):
            if not _has_cite(e, field):
                assert e[field] is None, f"{e['name']}: unsourced {field} published"
        if not _has_cite(e, "composite_score"):
            assert e["composite_score"] is None and e["grade"] is None, f"{e['name']}: unsourced rating published"
        if not _has_cite(e, "regulatory_citations"):
            assert e["regulatory_citations"] == [], f"{e['name']}: unsourced regulatory citation published"
        if not _has_cite(e, "swap_name"):
            assert e["swap_slug"] is None and e["swap_type"] is None
        # Public output names withheld fields but never their values.
        assert all(set(w) == {"field", "reason"} for w in e["withheld_claims"])


def test_healthcare_api_compare(client):
    slugs = "unitedhealthcare-optum,plum-health-direct-primary-care"
    resp = client.get(f"/v1/healthcare/compare?slugs={slugs}")
    assert resp.status_code == 200
    comp = resp.json()

    assert comp["compared_count"] == 2
    assert len(comp["metrics_matrix"]["names"]) == 2
    assert comp["metrics_matrix"]["composite_score"] == [e["composite_score"] for e in comp["entities"]]

    # A winner is named only among entities with a cited rating.
    winner = comp["highest_integrity_entity"]
    rated = [e for e in comp["entities"] if e["composite_score"] is not None]
    if rated:
        assert winner["name"] == max(rated, key=lambda e: e["composite_score"])["name"]
    else:
        assert winner["name"] is None
        assert winner["rationale"] == WITHHELD_TEXT

    resp_404 = client.get("/v1/healthcare/compare?slugs=non-existent-entity-xyz")
    assert resp_404.status_code == 404


def test_healthcare_api_stats(client):
    resp = client.get("/v1/healthcare/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total_entities"] == len(VERIFIED_HEALTHCARE_ENTITIES)
    assert "averages" in stats
    # Averages are null when no value is cited; they are never a fabricated 0.0.
    for key, value in stats["averages"].items():
        assert value is None or isinstance(value, float), key

    everyone = client.get("/v1/healthcare/database?limit=1000").json()["entities"]
    # PE counts are null until at least one record has a cited PE determination
    if any(e["is_pe_rollup"] is not None for e in everyone):
        assert stats["pe_rollups_count"] == sum(1 for e in everyone if e["is_pe_rollup"] is True)
    else:
        assert stats["pe_rollups_count"] is None and stats["pe_rollups_pct"] is None
    assert sum(stats["by_ownership_tier"].values()) == sum(1 for e in everyone if e["ownership_tier"] is not None)


def test_healthcare_entity_detail_withholds_parent_filing_without_parent_link(client):
    """UnitedHealthcare (Optum) is a subsidiary. UnitedHealth Group's 10-K does not show that link on its own,
    so its payout share and parent name are withheld until the brand-to-parent link is cited."""
    resp = client.get("/v1/healthcare/unitedhealthcare-optum")
    assert resp.status_code == 200
    detail = resp.json()
    # Parenthetical descriptors such as "(Optum)" are removed from display names
    assert detail["name"] == "UnitedHealthcare"
    assert detail["data_provenance"] != "verified_sec_filing"
    assert detail.get("sec_receipt_details") is None
    assert detail["shareholder_extraction_pct"] is None
    assert detail.get("parent_organization") is None
    # The clinical-care estimate has no cited source, so it is withheld (and not labelled as published).
    assert detail["clinical_care_wages_pct"] is None
    assert detail["split_basis"].get("clinical_care_wages_pct") != "sec_filing"


def test_serialize_withholds_everything_without_a_cited_source():
    out = serialize_entity(_record())
    for field in CITED_ONLY + [
        "composite_score", "grade", "ownership_type", "ownership_tier", "parent_organization",
        "pe_firm_name", "is_pe_rollup", "exec_comp_pct", "shareholder_extraction_pct", "swap_slug", "swap_type",
    ]:
        assert out[field] is None, field
    assert out["regulatory_citations"] == []
    # Identity and location are not claims about ownership or performance and stay visible.
    assert out["name"] == "Example Clinic Group"
    assert out["city"] == "Austin"


def test_serialize_publishes_cited_values():
    out = serialize_entity(_record(claim_sources=CITED_SOURCES))
    assert out["medical_loss_ratio_pct"] == 83.5
    assert out["composite_score"] == 40 and out["grade"] == "D"
    assert out["is_pe_rollup"] is True and out["pe_firm_name"] == "Sponsor Capital LP"
    assert out["swap_name"] == "Local Direct Primary Care" and out["swap_slug"] == "local-direct-primary-care"
    assert out["swap_rationale"] == "Flat-fee physician practice."
    # Not cited, so still withheld.
    assert out["clinical_care_wages_pct"] is None
    assert out["ownership_tier"] is None


def test_sec_receipt_backs_parent_ownership_and_payout():
    receipt = {
        "filing_url": "https://www.sec.gov/Archives/edgar/data/731766/example.htm",
        "total_shareholder_payout_usd": "$1.0B",
    }
    out = serialize_entity(_record(
        parent_organization="Example Corp (Public: EXC)",
        ownership_type="public",
        ownership_tier=6,
        shareholder_extraction_pct=0.0,
        sec_receipt_details=receipt,
        source_citation="Example Corp Form 10-K",
        claim_sources={},
    ))
    assert out["parent_organization"] == "Example Corp (Public: EXC)"
    assert out["ownership_type"] == "public" and out["ownership_tier"] == 6
    # A filed zero is shown as a zero; the page words it as "no payout reported".
    assert out["shareholder_extraction_pct"] == 0.0
    assert out["clinical_care_wages_pct"] is None


def test_healthcare_web_view(client):
    resp = client.get("/healthcare")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Healthcare Comparisons" in resp.text
    assert "Side-by-Side Healthcare Comparison" in resp.text
    assert WITHHELD_TEXT in resp.text
    for phrase in FORBIDDEN_ON_PAGE:
        assert phrase not in resp.text, phrase


@pytest.fixture
def cited_client(tmp_path):
    """A client whose database holds one record with cited claims, in a throwaway SQLite file."""
    engine = create_engine(f"sqlite:///{(tmp_path / 'cited.db').as_posix()}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    with Session() as s:
        s.add(_record(claim_sources=CITED_SOURCES))
        s.commit()

    def _override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def test_healthcare_page_and_api_show_only_cited_values(cited_client):
    html = cited_client.get("/healthcare").text
    # Cited values render with their source link on the server-rendered path.
    assert "83.5%" in html and "https://example.gov/mlr-filing" in html
    assert "12.5%" in html and "https://example.gov/denials" in html
    assert "PE-owned (Sponsor Capital LP)" in html
    assert "Shoptegrity opinion" in html and "D (40)" in html
    assert "Local Direct Primary Care" in html and "Flat-fee physician practice." in html
    # Uncited values are withheld and their values never appear.
    assert "61.0" not in html and "20.0" not in html
    assert "2.1x" not in html
    assert "Example Holdings Inc." not in html
    assert "Consent order" not in html
    assert "PRIVATE EQUITY" not in html  # the card's uncited ownership chip; the filter dropdown is not a claim
    assert WITHHELD_TEXT in html
    for phrase in FORBIDDEN_ON_PAGE:
        assert phrase not in html, phrase

    entity = cited_client.get("/v1/healthcare/example-clinic-group").json()
    assert entity["medical_loss_ratio_pct"] == 83.5
    assert entity["clinical_care_wages_pct"] is None
    assert entity["ownership_tier"] is None
    assert cited_client.get("/v1/healthcare/database?is_pe_rollup=true").json()["total"] == 1
    assert cited_client.get("/v1/healthcare/database?tier=5").json()["total"] == 0
