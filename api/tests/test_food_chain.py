import pytest
from fastapi.testclient import TestClient
from api.app.main import app
from api.app.services.geo_flow_service import get_farm_gate_decomposition

client = TestClient(app)


def test_farmland_ownership_api():
    """Verify federal farmland ownership, tenancy statistics, and elite landowner holdings."""
    res = client.get("/v1/food/farmland-ownership")
    assert res.status_code == 200
    data = res.json()

    assert data["rented_percentage"] == 39.2
    assert data["rented_acres"] == "348,000,000"
    assert data["non_operator_landlord_pct"] == 80.0
    assert data["non_operators_never_farmed_pct"] == 52.3
    assert data["corn_belt_rented_pct_range"] == "53% – 65%"
    assert data["owner_operator_pct"] == 60.8
    assert data["top_100_landowners_pct"] == 1.6

    owners = data["top_elite_landowners"]
    assert len(owners) >= 7

    names = [o["name"] for o in owners]
    assert any("Bill Gates" in n for n in names)
    assert any("Stan Kroenke" in n for n in names)
    assert any("Stewart & Lynda Resnick" in n for n in names)
    assert any("Jeff Bezos" in n for n in names)
    assert any("John Malone" in n for n in names)

    gates = next(o for o in owners if "Bill Gates" in o["name"])
    assert gates["acreage"] == 275000
    assert "cropland" in gates["primary_holdings"].lower()

    resnicks = next(o for o in owners if "Resnick" in o["name"])
    assert "Kern Water Bank" in resnicks["water_and_resource_notes"]

    assert len(data["sources"]) >= 4
    assert any("USDA" in s for s in data["sources"])
    assert any("Land Report 100" in s for s in data["sources"])


def test_farm_budgets_api():
    """Verify enterprise cost-of-production budgets and arithmetic balance."""
    res = client.get("/v1/food/farm-budgets")
    assert res.status_code == 200
    data = res.json()

    assert "comparisons" in data
    budgets = data["comparisons"]
    assert len(budgets) == 3

    # Check each budget for exact 100% balance
    for b in budgets:
        assert b["gross_farm_gate"] == 100.0
        exp_sum = sum(e["amount"] for e in b["expenses"])
        pct_sum = sum(e["pct"] for e in b["expenses"])

        # Strictly balanced: deductions + take-home == gross farm gate
        assert round(exp_sum + b["net_farmer_income"], 2) == 100.00
        assert round(pct_sum + b["net_farmer_pct"], 2) == 100.00

    # Commodity Grain
    grain = next(b for b in budgets if b["id"] == "commodity_corn_soy")
    assert grain["net_farmer_pct"] == 7.0
    assert any("Cash Rent" in e["name"] for e in grain["expenses"])
    assert any("Fertilizer" in e["name"] for e in grain["expenses"])
    assert any("Machinery" in e["name"] for e in grain["expenses"])
    assert any("Patented GMO Seed" in e["name"] for e in grain["expenses"])

    # Captive Poultry CAFO
    poultry = next(b for b in budgets if b["id"] == "contract_poultry_cafo")
    assert poultry["net_farmer_pct"] == 15.0
    assert any("Mortgage Debt" in e["name"] for e in poultry["expenses"])

    # Independent Regenerative Co-op
    regen = next(b for b in budgets if b["id"] == "independent_community_farm")
    assert regen["net_farmer_pct"] == 65.0
    seed_exp = next(e for e in regen["expenses"] if "GMO Seed" in e["name"])
    assert seed_exp["amount"] == 0.0


def test_food_html_view_renders_all_sections():
    """Verify HTML template renders the new tenancy, paradox, elite owner, and budget sections."""
    res = client.get("/food")
    assert res.status_code == 200
    html = res.text

    # Hero Jump Anchors
    assert "#farmland-ownership" in html
    assert "#farm-budgets" in html

    # Section 3: Tenancy & Landlord Matrix
    assert "Who Owns America&#39;s Farmland?" in html or "Who Owns America's Farmland?" in html
    assert "39.2%" in html
    assert "348,000,000 acres" in html
    assert "Non-Operator Landlords" in html
    assert "52.3%" in html
    assert "Corn Belt Tenancy" in html
    assert "Top 100 Private Landowners" in html

    # Conglomerate Paradox Box
    assert "The Conglomerate Paradox: Why Big Ag Avoids Owning the Dirt" in html
    assert "Tyson Foods" in html or "Tyson" in html
    assert "Captive Vertical Contracts" in html
    assert "99.5% of broilers" in html
    assert "$1.5M to $2.5M" in html

    # Elite Landowners Spotlight
    assert "The New Landed Gentry" in html
    assert "Stan Kroenke" in html
    assert "Bill Gates" in html
    assert "Stewart &amp; Lynda Resnick" in html or "Stewart & Lynda Resnick" in html
    assert "Kern Water Bank" in html

    # Section 4: Cost of Production & Take-Home
    assert "Where Does Farm Revenue Go?" in html
    assert "Conventional Commodity Grain" in html
    assert "Captive Contract Poultry Grower" in html
    assert "Independent Regenerative Family Farm" in html
    assert "7% Net Take-Home" in html or "7.0% Net Take-Home" in html
    assert "65% Net Take-Home" in html or "65.0% Net Take-Home" in html

    # 3 Survival Mechanisms
    assert "The 3 Survival Mechanisms" in html
    assert "Off-Farm Day Jobs" in html
    assert "82%+" in html
    assert "Federal Safety-Net Subsidies" in html
    assert "Generational Debt-Free Dirt" in html


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
