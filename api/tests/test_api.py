import pytest
from fastapi.testclient import TestClient
from api.app.main import app

client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_web_portal_views():
    # Landing Portal Home
    res_home = client.get("/")
    assert res_home.status_code == 200
    assert "Shoptegrity" in res_home.text
    assert "Food Chain Integrity" in res_home.text
    assert "Brand Integrity" in res_home.text

    # Brands View
    res_brands = client.get("/brands")
    assert res_brands.status_code == 200
    assert "Annie&#39;s Homegrown" in res_brands.text or "Annie's" in res_brands.text
    assert "General Mills" in res_brands.text

    # Brand Detail View
    res_detail = client.get("/brands/annies-homegrown")
    assert res_detail.status_code == 200
    assert "General Mills" in res_detail.text
    assert "Six-Dimension Integrity Scorecard" in res_detail.text
    assert "Organic Valley" in res_detail.text

    # Food Chain View
    res_food = client.get("/food")
    assert res_food.status_code == 200
    assert "Universal Food Sourcing Ladder" in res_food.text
    assert "Food Dollar" in res_food.text
    assert "Table Rock Tea" in res_food.text

    # Local Directory View
    res_local = client.get("/local")
    assert res_local.status_code == 200
    assert "Local Services Ownership Ladder" in res_local.text
    assert "Minneapolis Metro Plumbing" in res_local.text
    assert "DISGUISED PE ROLLUP" in res_local.text

    # Swaps View
    res_swaps = client.get("/swaps")
    assert res_swaps.status_code == 200
    assert "Credit Unions" in res_swaps.text

    # Flows View
    res_flows = client.get("/flows")
    assert res_flows.status_code == 200
    assert "Dollar Flow Map" in res_flows.text

    # Methodology View
    res_method = client.get("/methodology")
    assert res_method.status_code == 200
    assert "Integrity Firewall Policy" in res_method.text


def test_brands_api():
    res = client.get("/v1/brands")
    assert res.status_code == 200
    brands = res.json()
    assert len(brands) >= 5

    res_search = client.get("/v1/brands?q=annie")
    assert res_search.status_code == 200
    found = res_search.json()
    assert any("Annie" in b["name"] for b in found)

    res_detail = client.get("/v1/brands/annies-homegrown")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["name"] == "Annie's Homegrown"
    assert detail["parent_entity"]["name"] == "General Mills, Inc."
    assert "ownership" in detail["scorecard"]
    assert "pay_equity" in detail["scorecard"]
    assert len(detail["alternatives"]) >= 1


def test_food_chain_api():
    res_ladder = client.get("/v1/food/sourcing-ladder")
    assert res_ladder.status_code == 200
    data = res_ladder.json()
    assert len(data["tiers"]) == 9

    res_split = client.get("/v1/food/dollar-split")
    assert res_split.status_code == 200
    splits = res_split.json()
    assert len(splits) >= 3
    overall = next(s for s in splits if "Overall" in s["product_category"])
    assert overall["farm_share_cents"] == 11.8

    res_makers = client.get("/v1/food/makers")
    assert res_makers.status_code == 200
    makers = res_makers.json()
    assert any("Table Rock" in m["name"] for m in makers)
    assert any("American Classic" in m["name"] for m in makers)


def test_local_places_api_and_pe_match():
    res_places = client.get("/v1/local/places?lat=44.9778&lon=-93.2650&radius_km=25")
    assert res_places.status_code == 200
    places = res_places.json()
    assert len(places) >= 3

    res_pe = client.post(
        "/v1/local/match",
        json={"name": "Minneapolis Metro Plumbing & Heating"},
    )
    assert res_pe.status_code == 200
    match_data = res_pe.json()
    assert match_data["matched"] is True
    assert match_data["warning_flag"] == "DISGUISED_ROLLUP"
    assert "Apex Service Partners" in match_data["ownership_explanation"]


def test_methodology_api():
    res = client.get("/v1/methodology")
    assert res.status_code == 200
    data = res.json()
    assert data["rubric_version"] == "1.0.0"
    assert len(data["data_sources"]) >= 5
    assert "integrity_firewall_policy" in data
