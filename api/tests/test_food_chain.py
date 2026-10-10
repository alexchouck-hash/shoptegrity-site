import pytest
from fastapi.testclient import TestClient
from api.app.main import app
from api.app.routers import web_views
from api.app.routers.food_chain import FoodDollarSplitPublic
from api.app.services.geo_flow_service import get_farm_gate_decomposition

client = TestClient(app)

WITHHELD = "Withheld: no cited source yet"
LISTED = "Listed, not verified"


def test_sourcing_ladder_api():
    """Tier names and descriptions are a labelled framework; producer shares are withheld; ordering criterion is stated."""
    res = client.get("/v1/food/sourcing-ladder")
    assert res.status_code == 200
    data = res.json()

    assert "Shoptegrity opinion" in data["title"]
    assert "framework judgment" in data["description"]
    assert "not computed from producer dollar shares" in data["description"]

    tiers = data["tiers"]
    assert [t["tier"] for t in tiers] == list(range(1, 10))
    for t in tiers:
        assert t["producer_dollar_share_pct"] is None
        assert "%" not in t["description"]
        assert "¢" not in t["description"]
        assert "%" not in t["recommendation"]


def test_farmland_ownership_api():
    """Statistics without a cited source are null; landowner profiles and source names are removed."""
    res = client.get("/v1/food/farmland-ownership")
    assert res.status_code == 200
    data = res.json()

    for key in [
        "total_us_farmland_acres",
        "rented_percentage",
        "rented_acres",
        "non_operator_landlord_pct",
        "non_operators_never_farmed_pct",
        "corn_belt_rented_pct_range",
        "owner_operator_pct",
        "institutional_investor_pct",
        "foreign_investor_pct",
        "top_100_landowners_pct",
    ]:
        assert key in data, key
        assert data[key] is None, key

    # Key names are kept; the named landowner profiles and unlinked source names are removed.
    assert data["top_elite_landowners"] == []
    assert data["sources"] == []

    for name in ["Kroenke", "Emmerson", "Malone", "Ted Turner", "Bezos", "Bill Gates", "Resnick", "Kern Water Bank", "Land Report"]:
        assert name not in res.text


def test_farm_budgets_api():
    """Enterprise cost categories keep their keys; amounts, shares, beneficiaries and take-home figures are withheld."""
    res = client.get("/v1/food/farm-budgets")
    assert res.status_code == 200
    data = res.json()

    assert "comparisons" in data
    budgets = data["comparisons"]
    assert [b["id"] for b in budgets] == [
        "commodity_corn_soy",
        "contract_poultry_cafo",
        "independent_community_farm",
    ]

    for b in budgets:
        assert b["gross_farm_gate"] is None
        assert b["retail_context"] == WITHHELD
        assert b["net_farmer_income"] is None
        assert b["net_farmer_pct"] is None
        assert b["take_home_notes"] == WITHHELD
        assert len(b["expenses"]) >= 3
        for e in b["expenses"]:
            assert e["amount"] is None
            assert e["pct"] is None
            assert e["beneficiaries"] == WITHHELD
            assert "color" in e

    grain = next(b for b in budgets if b["id"] == "commodity_corn_soy")
    assert any("Cash Rent" in e["name"] for e in grain["expenses"])
    assert any("Fertilizer" in e["name"] for e in grain["expenses"])
    assert any("Machinery" in e["name"] for e in grain["expenses"])
    assert any("Patented GMO Seed" in e["name"] for e in grain["expenses"])

    # No named company appears as a beneficiary or anywhere in the budget payload.
    for company in ["Nutrien", "CF Industries", "Mosaic", "Deere", "CNH", "Bayer", "Monsanto", "Corteva", "BASF", "Syngenta", "Tyson", "JBS", "Smithfield", "Cargill"]:
        assert company not in res.text


def test_dollar_split_api():
    """Every ERS-attributed figure, year and citation is null or withheld; category labels are kept."""
    res = client.get("/v1/food/dollar-split")
    assert res.status_code == 200
    splits = res.json()
    assert len(splits) == 4

    numeric_keys = [
        "farm_share_cents",
        "food_processing_cents",
        "packaging_cents",
        "transportation_cents",
        "wholesale_trade_cents",
        "retail_trade_cents",
        "food_services_cents",
        "energy_cents",
        "finance_insurance_cents",
        "advertising_cents",
        "other_cents",
        "year",
    ]
    for s in splits:
        for k in numeric_keys:
            assert s[k] is None, k
        assert s["source_citation"] == WITHHELD
        assert s["summary_insight"] == WITHHELD

    assert any("Overall" in s["product_category"] for s in splits)

    for figure in ["11.8", "14.5", "14.70", "USDA ERS"]:
        assert figure not in res.text

    filtered = client.get("/v1/food/dollar-split?category=Dairy").json()
    assert [s["product_category"] for s in filtered] == ["Dairy & Fluid Milk"]


def test_makers_api_withholds_claims():
    """Maker names, makes-own status, certifications and verification are withheld; the entries stay listed."""
    res = client.get("/v1/food/makers")
    assert res.status_code == 200
    makers = res.json()
    assert makers, "maker registry should not be empty"

    for m in makers:
        assert m["name"] == LISTED
        assert m["makes_own"] is None
        assert m["makes_own_evidence"] == WITHHELD
        assert m["certifications"] == []
        assert m["products"]
        if m["place"]:
            assert m["place"]["name"] == LISTED
            assert m["place"]["verified_locally"] is None
            assert m["place"]["verified_how"] == WITHHELD
            assert m["place"]["ownership_tier"] is None
            assert m["place"]["flags"] == []

    for claim in [
        "Naturally Grown",
        "League of Tea Growers",
        "Certified Organic Farm",
        "Bigelow",
        "Table Rock Tea Farm",
        "Camellia Forest",
        "American Classic Tea",
        "Tangletown Farm",
        "Owned by",
        "Verified",
    ]:
        assert claim not in res.text


def test_makers_organic_filter_returns_nothing():
    """Certifications are withheld, so no entry can be matched on an organic certification."""
    res = client.get("/v1/food/makers?organic_only=true")
    assert res.status_code == 200
    assert res.json() == []


def test_food_html_view_renders_all_sections():
    """Verify the food page keeps its sections and shows withheld text where figures and claims were removed."""
    res = client.get("/food")
    assert res.status_code == 200
    html = res.text

    # Hero Jump Anchors
    assert "#farmland-ownership" in html
    assert "#farm-budgets" in html
    assert "#ladder" in html
    assert "#dollar-split" in html
    assert "#makers" in html

    # Ladder: labelled framework, shares withheld
    assert "The Universal Food Sourcing Ladder" in html
    assert "Shoptegrity opinion" in html
    assert WITHHELD in html

    # Dollar split: figures withheld
    assert "Where Does Your Food Dollar Land?" in html
    assert "Overall U.S. Food Average" in html
    assert "11.8" not in html
    assert "14.5" not in html
    assert "$100" not in html

    # Tenancy & landowners: figures withheld, no unsourced characterizations
    assert "Who Owns America's Farmland?" in html or "Who Owns America&#39;s Farmland?" in html
    assert "Non-Operator Landlords" in html
    assert "Corn Belt Tenancy" in html
    assert "Top 100 Private Landowners" in html
    for old in ["39.2%", "348,000,000", "52.3%", "80.0%", "14.5 million", "99.5% of broilers", "$1.5M", "82%+", "8 out of 10", "never operated"]:
        assert old not in html

    # Production contracts card: generic guidance, no named companies
    assert "How Production Contracts Divide Risk" in html
    assert "Read the Contract" in html
    for company in ["Tyson", "JBS", "Smithfield", "Cargill"]:
        assert company not in html

    # Largest landowners: withheld, no names
    assert "Largest Private Landowners" in html
    for name in ["Stan Kroenke", "Bill Gates", "Resnick", "Jeff Bezos", "Kern Water Bank", "Waggoner"]:
        assert name not in html

    # Cost of production: withheld, no named companies, no composite $100 example
    assert "Where Does Farm Revenue Go?" in html
    assert "Conventional Commodity Grain" in html
    assert "Contract Poultry Grower" in html
    assert "Independent Family Farm" in html
    for old in ["7% Net Take-Home", "65% Net Take-Home", "$14.70", "11.8¢", "93%", "28%", "Beneficiaries:"]:
        assert old not in html
    for company in ["Nutrien", "Bayer", "Deere"]:
        assert company not in html

    # 3 Survival Mechanisms
    assert "The 3 Survival Mechanisms" in html
    assert "Off-Farm Day Jobs" in html
    assert "Federal Safety-Net Subsidies" in html
    assert "Generational Debt-Free Dirt" in html

    # Makers and local places: listed, not verified; claims withheld
    assert "Small Maker &amp; Grower Registry" in html or "Small Maker & Grower Registry" in html
    assert LISTED in html
    assert "Table Rock Tea Farm" not in html

    # Partner, verified, and source-line wording removed
    assert "Partner Site" not in html
    assert "Verified direct growers" not in html
    assert "Verified democratic" not in html
    assert "Land Report" not in html
    assert "USDA ERS" not in html
    assert "100% of wealth" not in html
    assert "Over 3x" not in html
    assert "over 5x" not in html.lower()
    assert "SNAP / EBT Accepted" not in html


def test_food_page_renders_figures_when_present(monkeypatch):
    """The figure branch of the dollar-split card still renders if cited figures are later supplied."""
    sample = FoodDollarSplitPublic(
        product_category="Test Category",
        farm_share_cents=20.0,
        food_processing_cents=10.0,
        packaging_cents=5.0,
        transportation_cents=5.0,
        wholesale_trade_cents=15.0,
        retail_trade_cents=30.0,
        food_services_cents=0.0,
        energy_cents=5.0,
        finance_insurance_cents=3.0,
        advertising_cents=7.0,
        other_cents=0.0,
        year=2024,
        source_citation="Test fixture",
        summary_insight="Test fixture",
    )
    monkeypatch.setattr(web_views, "fetch_food_dollar_splits", lambda: [sample])

    res = client.get("/food")
    assert res.status_code == 200
    assert "Test Category" in res.text
    assert "Actual Grower Share" in res.text


def test_flows_farm_gate_audit_drawer():
    """Verify Dollar Flow Map renders the farm gate decomposition audit in farm nodes."""
    res = client.get("/flows?scenario=cereal_conventional&spend=100")
    assert res.status_code == 200
    html = res.text

    assert "Farm-Gate Audit: What Does the Farmer Actually Pocket?" in html
    assert "Cash Rent &amp; Land Mortgage" in html or "Cash Rent & Land Mortgage" in html
    assert "Synthetic Fertilizer (NPK)" in html
    assert "Net Farmer Take-Home" in html

    # Verify Co-op alternative farm gate audit
    res_coop = client.get("/flows?scenario=cereal_coop&spend=100")
    assert res_coop.status_code == 200
    html_coop = res_coop.text
    assert "Farmer Living Return" in html_coop


def test_get_farm_gate_decomposition_service():
    """Direct unit testing of the geo_flow_service decomposition function."""
    # Conventional grain/produce decomposition on $14.70
    audit_grain = get_farm_gate_decomposition("grocery_produce", "contract_grower", 14.70)
    assert audit_grain is not None
    assert audit_grain.gross_farm_gate_amount == 14.70
    assert audit_grain.net_farmer_take_home_amount == 1.02
    assert audit_grain.net_farmer_take_home_pct == 6.9
    assert len(audit_grain.input_expenses) == 7

    # Conventional grain/produce decomposition on $100.00
    audit_grain_100 = get_farm_gate_decomposition("grocery_produce", "contract_grower", 100.00)
    assert audit_grain_100.net_farmer_take_home_amount == 7.00
    assert audit_grain_100.net_farmer_take_home_pct == 7.0

    # Poultry decomposition
    audit_poultry = get_farm_gate_decomposition("meat_poultry", "contract_grower", 11.20)
    assert audit_poultry is not None
    assert audit_poultry.net_farmer_take_home_pct == 15.0
    assert audit_poultry.net_farmer_take_home_amount == 1.68

    # Regenerative co-op decomposition
    audit_coop = get_farm_gate_decomposition("grocery_produce", "community_farmer", 42.00)
    assert audit_coop is not None
    assert audit_coop.net_farmer_take_home_pct == 65.0
    assert audit_coop.net_farmer_take_home_amount == 27.30

    # Non-farm tier returns None
    assert get_farm_gate_decomposition("grocery_produce", "retail", 50.00) is None
    assert get_farm_gate_decomposition("grocery_produce", "contract_grower", 0.0) is None
