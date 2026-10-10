"""Local directory and rubric gate tests: sourced or withheld.

Run with --noconftest and a scratch DATABASE_URL. The root conftest re-seeds the
database and rewrites api/v1 JSON files, so it is not loaded here. These tests
build their own rows and never touch shoptegrity.db.
"""
import os

import pytest
from fastapi.testclient import TestClient

from api.app.db.session import SessionLocal, engine, init_db
from api.app.main import app
from api.app.models.core import Base, Entity, Evidence, Place
from rubric.engine import compute_scores, load_rubric

client = TestClient(app)

CITED_URL = "https://example.org/ownership-record"


@pytest.fixture(scope="module", autouse=True)
def local_rows():
    url = os.environ.get("DATABASE_URL", "")
    if not url or url.endswith("shoptegrity.db"):
        pytest.skip("set DATABASE_URL to a scratch database to run these tests")

    Base.metadata.drop_all(bind=engine)
    init_db()
    db = SessionLocal()

    db.add(Entity(
        id="ent-test-cited", name="Test Holdings Group", slug="test-holdings-group",
        kind="pe_firm", ownership_type="private_equity", locality_tier="unknown",
    ))
    db.add(Evidence(
        entity_id="ent-test-cited", dimension="ownership", fact_text="Test ownership record.",
        source_url=CITED_URL, source_name="Example Registry", source_type="trade_press",
        retrieved_at="2026-09-01", impact=-2, status="published",
    ))
    # Same owner, but the record is pending review, so it must not count as cited.
    db.add(Entity(
        id="ent-test-pending", name="Pending Holdings", slug="pending-holdings",
        kind="pe_firm", ownership_type="private_equity", locality_tier="unknown",
    ))
    db.add(Evidence(
        entity_id="ent-test-pending", dimension="ownership", fact_text="Unreviewed record.",
        source_url="https://example.org/pending", source_name="Pending Source", source_type="trade_press",
        retrieved_at="2026-09-01", impact=-2,
    ))

    db.add(Place(
        id="t-harbor", name="Harbor Plumbing Services", slug="harbor-plumbing", category="plumber",
        address="1 Harbor Way", city="St. Paul", state="MN", postal_code="55104",
        lat=44.9556, lon=-93.1612, entity_id="ent-test-cited", ownership_tier=6,
        flags=["rollup_disguised"], verified_locally=True, verified_how="Test verification",
    ))
    db.add(Place(
        id="t-lakeside", name="Lakeside Electric Works", slug="lakeside-electric", category="electrician",
        address="2 Lake Rd", city="St. Paul", state="MN", postal_code="55104",
        lat=44.9600, lon=-93.1700, ownership_tier=6, flags=["rollup_disguised"],
    ))
    db.add(Place(
        id="t-pending", name="Pending Plumbing Co", slug="pending-plumbing", category="plumber",
        address="3 Pend St", city="St. Paul", state="MN", postal_code="55104",
        lat=44.9500, lon=-93.1500, entity_id="ent-test-pending", ownership_tier=6,
        flags=["rollup_disguised"],
    ))
    db.add(Place(
        id="t-demo", name="Example Rollup Plumbing (Illustrative Demo Listing)", slug="demo-listing",
        category="plumber", address="Illustrative example", city="St. Paul", state="MN", postal_code="55104",
        lat=44.9556, lon=-93.1612, ownership_tier=6, flags=["rollup_disguised", "demo_listing"],
    ))
    db.add(Place(
        id="t-seward", name="Seward Community Co-op (Franklin)", slug="seward-test", category="food_coop",
        address="2823 E Franklin Ave", city="Minneapolis", state="MN", postal_code="55406",
        lat=44.9631, lon=-93.2305, ownership_tier=1, flags=["coop"],
    ))
    db.commit()
    db.close()
    yield


def _match(name, **extra):
    body = {"name": name}
    body.update(extra)
    res = client.post("/v1/local/match", json=body)
    assert res.status_code == 200
    return res.json()


def test_short_query_is_refused():
    data = _match("ab")
    assert data["matched"] is False
    assert data["place"] is None
    assert "at least 3 characters" in data["ownership_explanation"]


def test_single_shared_word_does_not_match():
    data = _match("Harbor")
    assert data["matched"] is False


def test_full_name_with_cited_record_gets_caution_with_source():
    data = _match("Harbor Plumbing Services")
    assert data["matched"] is True
    assert data["warning_flag"] == "DISGUISED_ROLLUP"
    assert CITED_URL in data["ownership_explanation"]
    assert "Test Holdings" not in data["ownership_explanation"]


def test_rollup_without_cited_record_gets_no_caution():
    data = _match("Lakeside Electric Works")
    assert data["matched"] is True
    assert data["warning_flag"] is None
    assert "rollup_disguised" not in data["place"]["flags"]
    assert data["place"]["ownership_tier"] == 0
    assert "Withheld: no cited source yet" in data["ownership_explanation"]


def test_pending_ownership_record_is_not_cited():
    data = _match("Pending Plumbing Co")
    assert data["warning_flag"] is None
    assert data["place"]["ownership_tier"] == 0
    assert "pending" not in data["ownership_explanation"].lower()


def test_demo_listing_is_never_matched():
    data = _match("Example Rollup Plumbing (Illustrative Demo Listing)")
    assert data["matched"] is False
    assert data["warning_flag"] is None


def test_distance_threshold_rejects_far_coordinates():
    far = _match("Seward Community Co-op (Franklin)", lat=32.0, lon=-80.0)
    assert far["matched"] is False
    near = _match("Seward Community Co-op (Franklin)", lat=44.9631, lon=-93.2305)
    assert near["matched"] is True


def test_places_list_excludes_demo_listings():
    res = client.get("/v1/local/places")
    assert res.status_code == 200
    names = [p["name"] for p in res.json()]
    assert not any("Illustrative" in n for n in names)


def test_places_list_rollup_flag_only_for_cited_records():
    res = client.get("/v1/local/places", params={"flag": "rollup_disguised"})
    names = [p["name"] for p in res.json()]
    assert names == ["Harbor Plumbing Services"]


def test_places_list_max_tier_excludes_uncited_tiers():
    res = client.get("/v1/local/places", params={"max_tier": 6})
    names = [p["name"] for p in res.json()]
    assert "Harbor Plumbing Services" in names
    assert "Lakeside Electric Works" not in names


def test_local_page_has_no_hardcoded_firms_or_fabricated_claims():
    res = client.get("/local")
    assert res.status_code == 200
    text = res.text
    for banned in ("Alpine Investors", "Apex Service Partners", "Example Rollup Plumbing",
                   "Consumer Notice", "Tier 0", "Searching business registries", "100% of profits",
                   "Verified owner-operated"):
        assert banned not in text, banned
    assert "PRIVATE EQUITY OWNER (CITED)" in text
    assert "Withheld: no cited source yet" in text


def test_engine_withholds_every_dimension_without_cited_evidence():
    company = {
        "id": "x", "name": "X", "ownership_type": "worker_coop", "locality_tier": "owner_operated_local",
        "capital_extraction_ratio": 0.2, "ceo_pay_ratio": 20.0,
        "labor_signals": ["living_wage_certified"], "env_signals": ["usda_organic"],
    }
    uncited = [{"dimension": "ownership", "source_type": "certifier", "fact_text": "x", "source_url": "  "}]
    result = compute_scores(company, uncited, load_rubric())
    for dim in result.dimensions.values():
        assert dim.value is None
        assert dim.status == "unknown"
    assert result.composite_score is None


def test_engine_explanations_never_print_uncited_percentages_or_ratios():
    company = {"id": "y", "name": "Y", "ownership_type": "national_private",
               "locality_tier": "national_private", "capital_extraction_ratio": 0.85}
    evidence = [{"dimension": "capital_extraction", "source_type": "sec_edgar", "fact_text": "x",
                 "source_url": "https://www.sec.gov/example", "impact": 0}]
    result = compute_scores(company, evidence, load_rubric())
    explanation = result.dimensions["capital_extraction"].explanation
    assert "%" not in explanation
    assert result.dimensions["locality"].value is None


def test_engine_pluralizes_recorded_events():
    company = {"id": "z", "name": "Z", "ownership_type": "public", "locality_tier": "national_public"}
    evidence = [{"dimension": "labor", "source_type": "cfpb", "fact_text": "x",
                 "source_url": "https://www.consumerfinance.gov/example", "impact": -2}]
    result = compute_scores(company, evidence, load_rubric())
    assert "based on 1 recorded event." in result.dimensions["labor"].explanation
