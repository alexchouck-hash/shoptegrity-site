import pytest
from fastapi.testclient import TestClient
from api.app.main import app
from api.app.services.geo_flow_service import (
    resolve_zip,
    haversine_miles,
    trace_dollar_flow,
    SCENARIOS_META,
)

client = TestClient(app)


def test_resolve_zip_known_and_fallback():
    # Known ZIP code
    info_known = resolve_zip("55401")
    assert info_known["city"] == "Minneapolis"
    assert info_known["state"] == "MN"
    assert round(info_known["lat"], 2) == 44.98

    # Fallback ZIP code (prefix 9 -> Pacific Coast)
    info_fallback = resolve_zip("98001")
    assert info_fallback["zip"] == "98001"
    assert info_fallback["state"] == "CA" or info_fallback["city"] == "Pacific Coast"
    assert info_fallback["lat"] > 0


def test_haversine_miles():
    # Minneapolis (55401) to Plato, MN (55370) ~ 43 miles
    m = haversine_miles(44.9818, -93.2687, 44.7733, -94.0416)
    assert 35 < m < 50

    # Same location
    assert haversine_miles(44.9818, -93.2687, 44.9818, -93.2687) == 0.0


def test_trace_dollar_flow_grocery():
    trace = trace_dollar_flow(origin_zip="55401", scenario_id="grocery_produce", spend_amount=100.0)
    assert trace.origin_zip == "55401"
    assert trace.spend_amount == 100.0

    # Verify conventional nodes sum to ~100
    conv_total = sum(n.amount for n in trace.conventional.nodes)
    assert pytest.approx(conv_total, 0.5) == 100.0

    # Verify alternative nodes sum to ~100
    alt_total = sum(n.amount for n in trace.alternative.nodes)
    assert pytest.approx(alt_total, 0.5) == 100.0

    # Verify local retention is dramatically higher in alternative
    assert trace.alternative.local_retained_pct > trace.conventional.local_retained_pct
    assert trace.alternative.local_retained_pct >= 70.0

    # Verify worker/farmer share
    assert trace.alternative.worker_farmer_pct > trace.conventional.worker_farmer_pct

    # Verify farm ownership tier on grocery
    conv_farm_nodes = [n for n in trace.conventional.nodes if n.farm_ownership_tier]
    assert len(conv_farm_nodes) >= 1
    assert conv_farm_nodes[0].farm_ownership_tier == "contract_grower"

    alt_farm_nodes = [n for n in trace.alternative.nodes if n.farm_ownership_tier]
    assert len(alt_farm_nodes) >= 1
    assert alt_farm_nodes[0].farm_ownership_tier == "community_farmer"


def test_trace_dollar_flow_meat_poultry():
    trace = trace_dollar_flow(origin_zip="55401", scenario_id="meat_poultry", spend_amount=100.0)
    assert trace.scenario_id == "meat_poultry"

    # Wall street / PE extraction present in conventional
    assert trace.conventional.executive_shareholder_amount > 0
    # Zero Wall Street extraction in pasture alternative
    assert trace.alternative.executive_shareholder_amount == 0.0

    # Verify community farmer captures large share direct
    alt_farm = next(n for n in trace.alternative.nodes if n.farm_ownership_tier == "community_farmer")
    assert alt_farm.amount >= 70.0


def test_api_geo_scenarios_endpoint():
    response = client.get("/v1/flows/geo/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 4
    scenario_ids = [s["id"] for s in data]
    assert "grocery_produce" in scenario_ids
    assert "meat_poultry" in scenario_ids
    assert "banking_services" in scenario_ids
    assert "home_services" in scenario_ids


def test_api_geo_trace_endpoint():
    response = client.get("/v1/flows/geo/trace?origin_zip=60601&scenario_id=meat_poultry&spend=150.0")
    assert response.status_code == 200
    data = response.json()
    assert data["origin_zip"] == "60601"
    assert data["spend_amount"] == 150.0
    assert len(data["conventional"]["nodes"]) > 0
    assert len(data["alternative"]["nodes"]) > 0
    assert data["conventional"]["total_spend"] == 150.0
    assert data["alternative"]["total_spend"] == 150.0


def test_web_flows_view_html():
    response = client.get("/flows?zip=55401&scenario=grocery_produce&spend=100")
    assert response.status_code == 200
    assert "The Dollar Flow Map" in response.text
    assert "Interactive Geographic Map" in response.text
    assert "Option A: Conventional Corporate Chain" in response.text
    assert "VERIFIED INDEPENDENT COMMUNITY FARMER" in response.text
    assert "Total Financial Allocation" in response.text
    assert "Methodology & Data Integrity" in response.text
    assert "USDA Economic Research Service (ERS)" in response.text
    assert "SEC Form 10-K Filings" in response.text
    assert "National Co+op Grocers (NCG)" in response.text


@pytest.mark.parametrize("scenario_id", [s.id for s in SCENARIOS_META])
@pytest.mark.parametrize("spend", [50.0, 100.0, 245.50])
def test_all_scenarios_strictly_balance(scenario_id, spend):
    trace = trace_dollar_flow(origin_zip="55401", scenario_id=scenario_id, spend_amount=spend)
    assert trace.spend_amount == spend

    for branch in [trace.conventional, trace.alternative]:
        # 1. Geographic balance: local + flight == spend
        geo_sum = branch.local_retained_amount + branch.capital_flight_amount
        assert pytest.approx(geo_sum, 0.01) == spend
        assert pytest.approx(branch.local_retained_pct + branch.capital_flight_pct, 0.1) == 100.0

        # 2. Functional balance: worker + ops + exec + member == spend
        func_sum = (
            branch.worker_farmer_amount
            + branch.operations_logistics_amount
            + branch.executive_shareholder_amount
            + branch.member_dividends_amount
        )
        assert pytest.approx(func_sum, 0.01) == spend

        # 3. Functional percentage sum == 100.0%
        pct_sum = (
            branch.worker_farmer_pct
            + branch.operations_logistics_pct
            + branch.executive_shareholder_pct
            + branch.member_dividends_pct
        )
        assert pytest.approx(pct_sum, 0.1) == 100.0

        # 4. Sum of all step nodes == spend to the penny
        node_sum = sum(n.amount for n in branch.nodes)
        assert pytest.approx(node_sum, 0.01) == spend


