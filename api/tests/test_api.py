import pytest
from fastapi.testclient import TestClient
from api.app.main import app

client = TestClient(app)

WITHHELD = "Withheld: no cited source yet"


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_web_portal_views():
    # Landing portal: cause picker and platform cards
    res_home = client.get("/")
    assert res_home.status_code == 200
    assert "Shoptegrity" in res_home.text
    assert "Food Chain" in res_home.text
    assert "Brand Check & Swaps" in res_home.text
    assert 'id="causes"' in res_home.text
    assert "/static/js/causes.js" in res_home.text

    # Brands listing: parent companies are withheld until a cited ownership source exists
    res_brands = client.get("/brands")
    assert res_brands.status_code == 200
    assert "Annie&#39;s Homegrown" in res_brands.text or "Annie's" in res_brands.text
    assert WITHHELD in res_brands.text

    # Brand detail: ownership is withheld, and the scorecard is still shown
    res_detail = client.get("/brands/annies-homegrown")
    assert res_detail.status_code == 200
    assert "Ultimate Parent Company" in res_detail.text
    assert "General Mills" not in res_detail.text
    assert WITHHELD in res_detail.text

    # Food chain: unsourced figures are withheld
    res_food = client.get("/food")
    assert res_food.status_code == 200
    assert WITHHELD in res_food.text

    # Local directory: demo listings are never shown
    res_local = client.get("/local")
    assert res_local.status_code == 200
    assert "Example Rollup Plumbing" not in res_local.text

    # Swaps view: retailer figures are withheld
    res_swaps = client.get("/swaps")
    assert res_swaps.status_code == 200
    assert WITHHELD in res_swaps.text

    # Flows view
    res_flows = client.get("/flows")
    assert res_flows.status_code == 200
    assert "Dollar Flow Map" in res_flows.text

    # Methodology view
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
    # Parent company is withheld until cited
    assert all(b["parent_company_name"] is None for b in found)

    res_detail = client.get("/v1/brands/annies-homegrown")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["name"] == "Annie's Homegrown"
    assert detail["parent_entity"]["name"] is None
    assert detail["description"] is None
    assert "ownership" in detail["scorecard"]
    assert "pay_equity" in detail["scorecard"]
    # Swap recommendations are served only after editor approval (none are approved yet)
    assert detail["alternatives"] == []

    # Brands Database Endpoint: keys stay, withheld values are null
    res_db = client.get("/v1/brands/database?limit=10")
    assert res_db.status_code == 200
    db_data = res_db.json()
    assert 50 <= db_data["total"] < 1000  # curated records only, no generated filler
    assert len(db_data["brands"]) == 10
    first_b = db_data["brands"][0]
    assert "worker_wages_pct" in first_b
    assert "shareholder_extraction_pct" in first_b
    assert "labor_exploitation_rating" in first_b
    assert "waste_rating" in first_b

    # Major Retailers Endpoint
    res_ret = client.get("/v1/brands/retailers")
    assert res_ret.status_code == 200
    ret_data = res_ret.json()
    assert len(ret_data) >= 7
    ret_names = [r["name"] for r in ret_data]
    assert "Walmart" in ret_names
    assert "Costco Wholesale" in ret_names
    assert "Target" in ret_names


def test_food_chain_api():
    res_ladder = client.get("/v1/food/sourcing-ladder")
    assert res_ladder.status_code == 200
    data = res_ladder.json()
    assert len(data["tiers"]) == 9
    # Tier shares are withheld until cited
    assert all(t["producer_dollar_share_pct"] is None for t in data["tiers"])

    res_split = client.get("/v1/food/dollar-split")
    assert res_split.status_code == 200
    splits = res_split.json()
    assert len(splits) >= 3
    overall = next(s for s in splits if "Overall" in s["product_category"])
    # The farm-share figure is withheld until it is cited to the ERS table
    assert overall["farm_share_cents"] is None

    res_makers = client.get("/v1/food/makers")
    assert res_makers.status_code == 200
    makers = res_makers.json()
    assert len(makers) >= 1
    # Maker names and claims are withheld until cited; only the listing status is shown
    assert all(m["name"] == "Listed, not verified" for m in makers)
    assert all(m["makes_own"] is None and m["certifications"] == [] for m in makers)


def test_local_places_api_and_pe_match():
    res_places = client.get("/v1/local/places?lat=44.9778&lon=-93.2650&radius_km=25")
    assert res_places.status_code == 200
    places = res_places.json()
    assert len(places) >= 3
    # Demo listings are never served
    assert all("demo_listing" not in (p.get("flags") or []) for p in places)

    # The demo listing is gone, so it cannot match and cannot carry a rollup warning
    res_pe = client.post(
        "/v1/local/match",
        json={"name": "Example Rollup Plumbing"},
    )
    assert res_pe.status_code == 200
    match_data = res_pe.json()
    assert match_data["warning_flag"] is None
    assert "private equity" not in (match_data.get("ownership_explanation") or "").lower()


def test_methodology_api():
    res = client.get("/v1/methodology")
    assert res.status_code == 200
    data = res.json()
    assert data["rubric_version"] == "1.0.0"
    assert len(data["data_sources"]) >= 5
    assert "integrity_firewall_policy" in data


def test_swaps_api_dual_tiers():
    # 1. Swaps categories index
    res_cats = client.get("/v1/swaps")
    assert res_cats.status_code == 200
    categories = res_cats.json()
    assert len(categories) >= 5

    # 2. Banking category swap guide detail with Best vs Better
    res_banking = client.get("/v1/swaps/banking")
    assert res_banking.status_code == 200
    banking_data = res_banking.json()
    assert "guide" in banking_data
    guide = banking_data["guide"]
    assert "best_swap" in guide
    assert "better_swap" in guide

    # Savings figures are withheld until each has a cited source (R1)
    assert guide["best_swap"].get("average_savings") in (None, WITHHELD)

    # Editor-approved swap recommendations are served by name; rationale and where-to-buy stay withheld
    assert [a["brand_name"] for a in banking_data["best_alternatives"]] == ["Affinity Plus Credit Union Accounts"]
    assert [a["brand_name"] for a in banking_data["better_alternatives"]] == ["Alliant High-Yield Checking & Mobile Banking"]
    for card in banking_data["best_alternatives"] + banking_data["better_alternatives"]:
        assert card["rationale"] is None and card["where_to_buy"] is None and card["parent_name"] is None

    # Check Grocery category detail
    res_grocery = client.get("/v1/swaps/grocery")
    assert res_grocery.status_code == 200
    grocery_data = res_grocery.json()
    assert "guide" in grocery_data

    # Retailer dual swap details: names only, claims withheld
    res_ret = client.get("/v1/brands/retailers")
    assert res_ret.status_code == 200
    ret_list = res_ret.json()
    walmart = next(r for r in ret_list if r["name"] == "Walmart")
    assert "retailer_details" in walmart


def test_sell_direct_and_disclosure_pages():
    page = client.get("/sell-direct")
    assert page.status_code == 200
    assert "shopify.pxf.io/c/7862632/" in page.text
    assert 'rel="sponsored' in page.text
    assert "Affiliate disclosure" in page.text
    disc = client.get("/disclosures")
    assert disc.status_code == 200
    assert "Shopify" in disc.text
    # Affiliate links never appear on rating pages.
    for path in ["/brands", "/healthcare", "/swaps"]:
        assert "pxf.io" not in client.get(path).text


# Phrases that were removed from the public site under the sourced-or-withheld policy.
# If one of these comes back on a public page, it has been republished without a citation.
REMOVED_CLAIMS = [
    "Apex Service Partners",
    "Alpine Investors",
    "Verified PE Rollups",
    "100% Cited Evidence",
    "Zero brand advertising",
    "Top 10% Ownership Index",
    "Example Rollup Plumbing",
    "Sarah M.",
    "Dave R.",
    "Elena T.",
    "Precision Air",
    "Valley Animal Hospital",
    "Heritage Tree",
    "Kroenke",
    "Subterfuge",
    "Glass-Steagall",
    "Shoptegrity opinion rating under",
]


@pytest.mark.parametrize("path", [
    "/", "/brands", "/brands/annies-homegrown", "/healthcare", "/parents", "/food",
    "/local", "/swaps", "/flows", "/housing", "/community", "/methodology",
    "/corrections", "/disclosures", "/sell-direct",
])
def test_public_pages_carry_no_removed_claims(path):
    res = client.get(path)
    assert res.status_code == 200
    for phrase in REMOVED_CLAIMS:
        assert phrase not in res.text, f"{phrase!r} reappeared on {path}"
