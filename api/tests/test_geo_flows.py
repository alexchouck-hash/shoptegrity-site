import pytest
from fastapi.testclient import TestClient
from api.app.main import app
from api.app.services.geo_flow_service import (
    resolve_zip,
    haversine_miles,
    trace_dollar_flow,
    get_farm_gate_decomposition,
    SCENARIOS_META,
)

client = TestClient(app)

ALL_SCENARIO_IDS = [s.id for s in SCENARIOS_META]

# Named companies, named government programs and named sources that must not appear in the model output.
COMPANY_OR_PROGRAM_TERMS = [
    "Tyson", "Pilgrim", "Walmart", "Bentonville", "Springdale", "Malvern", "Wilmington",
    "BlackRock", "Vanguard", "State Street", "General Mills", "Realty Income", "Kroger",
    "Bayer", "Monsanto", "Deere", "Nutrien", "CF Industries", "Mosaic", "Corteva", "BASF",
    "Syngenta", "Bank of America", "Tangletown", "Wedge", "Midwest Organic", "Sovereignty",
    "Delaware", "Madison Avenue", "Federal Crop Insurance", "Farm Credit", "USDA", "PitchBook",
    "AELP", "FDIC", "Gracchi", "Standard Oil", "J.P. Morgan", "Glass-Steagall", "iShares", "Barclays",
]

# Accusatory or banned wording (owner policy R2) and the "capital flight" label.
BANNED_TERMS = [
    "captive", "disguised", "secretly", "deceive", "deception", "predatory", "exploitative",
    "co-conspirator", "conspiracy", "cartel", "monopol", "illegal", "siphon", "camouflage",
    "rigged", "theft", "wall street", "capital flight",
]

# City names of corporate headquarters that the old model used as locations.
HQ_CITY_NAMES = {"Bentonville", "Springdale", "Malvern", "Wilmington", "Golden Valley", "Charlotte"}
HQ_ZIPS = {"72716", "72764", "19355", "19801", "55426", "28202", "10005", "10055", "92078"}


def _trace_strings(trace):
    """Collects every text field of a trace so the wording can be checked in one place."""
    out = [trace.scenario_title, trace.comparison_insight]
    for branch in (trace.conventional, trace.alternative):
        out.extend([branch.display_title, branch.summary_text])
        for node in branch.nodes:
            out.extend([node.role, node.payee_name, node.city, node.state])
            if node.farm_ownership_notes:
                out.append(node.farm_ownership_notes)
            if node.farm_gate_audit:
                audit = node.farm_gate_audit
                out.extend([audit.title, audit.notes])
                for item in audit.input_expenses:
                    out.append(item.name)
                    out.extend(item.corporate_beneficiaries)
    return out


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

    # Verify local retention is higher in the alternative (modeled)
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

    # Shareholder-return category present in the conventional model
    assert trace.conventional.executive_shareholder_amount > 0
    # No shareholder-return category in the community model
    assert trace.alternative.executive_shareholder_amount == 0.0

    # Verify community farmer captures large share direct
    alt_farm = next(n for n in trace.alternative.nodes if n.farm_ownership_tier == "community_farmer")
    assert alt_farm.amount >= 70.0


def test_farm_gate_decomposition_values_unchanged():
    # Only labels changed; the modeled shares and residuals are the same as before.
    audit_grain = get_farm_gate_decomposition("grocery_produce", "contract_grower", 14.70)
    assert audit_grain.net_farmer_take_home_amount == 1.02
    assert audit_grain.net_farmer_take_home_pct == 6.9
    assert len(audit_grain.input_expenses) == 7

    audit_poultry = get_farm_gate_decomposition("meat_poultry", "contract_grower", 11.20)
    assert audit_poultry.net_farmer_take_home_pct == 15.0
    assert audit_poultry.net_farmer_take_home_amount == 1.68

    audit_coop = get_farm_gate_decomposition("grocery_produce", "community_farmer", 42.00)
    assert audit_coop.net_farmer_take_home_pct == 65.0
    assert audit_coop.net_farmer_take_home_amount == 27.30

    assert get_farm_gate_decomposition("grocery_produce", "retail", 50.00) is None
    assert get_farm_gate_decomposition("grocery_produce", "contract_grower", 0.0) is None


@pytest.mark.parametrize("scenario_id", ["grocery_produce", "meat_poultry"])
@pytest.mark.parametrize("tier", ["contract_grower", "community_farmer"])
def test_farm_gate_audit_is_labelled_and_category_level(scenario_id, tier):
    audit = get_farm_gate_decomposition(scenario_id, tier, 100.0)
    assert audit is not None
    assert "illustrative" in audit.title.lower()
    assert "not measurements" in audit.notes
    for item in audit.input_expenses:
        assert item.corporate_beneficiaries, item.name
        for beneficiary in item.corporate_beneficiaries:
            assert beneficiary.endswith("(category)"), beneficiary


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
    for s in data:
        assert "illustrative" in s["description"].lower()


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

    # Trace returns category-level payees only
    for branch in (data["conventional"], data["alternative"]):
        for node in branch["nodes"]:
            assert node["payee_name"].endswith("(category)"), node["payee_name"]


@pytest.mark.parametrize("scenario_id", ALL_SCENARIO_IDS)
@pytest.mark.parametrize("origin", ["55401", "60601", "98001"])
def test_payees_are_category_level(scenario_id, origin):
    trace = trace_dollar_flow(origin_zip=origin, scenario_id=scenario_id, spend_amount=100.0)
    for branch in (trace.conventional, trace.alternative):
        for node in branch.nodes:
            assert node.payee_name.endswith("(category)"), node.payee_name


@pytest.mark.parametrize("scenario_id", ALL_SCENARIO_IDS)
def test_trace_text_names_no_company_or_program(scenario_id):
    trace = trace_dollar_flow(origin_zip="55401", scenario_id=scenario_id, spend_amount=100.0)
    text = "\n".join(_trace_strings(trace)).lower()
    for term in COMPANY_OR_PROGRAM_TERMS:
        assert term.lower() not in text, term
    for term in BANNED_TERMS:
        assert term not in text, term


@pytest.mark.parametrize("scenario_id", ALL_SCENARIO_IDS)
def test_trace_locations_are_not_company_headquarters(scenario_id):
    trace = trace_dollar_flow(origin_zip="55401", scenario_id=scenario_id, spend_amount=100.0)
    for branch in (trace.conventional, trace.alternative):
        for node in branch.nodes:
            assert node.destination_zip not in HQ_ZIPS, node.destination_zip
            assert node.city not in HQ_CITY_NAMES, node.city


@pytest.mark.parametrize("scenario_id", ALL_SCENARIO_IDS)
def test_trace_insight_is_labelled_illustrative(scenario_id):
    trace = trace_dollar_flow(origin_zip="55401", scenario_id=scenario_id, spend_amount=100.0)
    assert "illustrative" in trace.comparison_insight.lower()
    assert "not measurements" in trace.comparison_insight
    assert "illustrative" in trace.scenario_title.lower()


@pytest.mark.parametrize("scenario_id", ALL_SCENARIO_IDS)
@pytest.mark.parametrize("spend", [50.0, 100.0, 245.50])
def test_all_scenarios_strictly_balance(scenario_id, spend):
    trace = trace_dollar_flow(origin_zip="55401", scenario_id=scenario_id, spend_amount=spend)
    assert trace.spend_amount == spend

    for branch in [trace.conventional, trace.alternative]:
        # 1. Geographic balance: local + out-of-area == spend
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


def test_macro_timeline_is_withheld():
    response = client.get("/v1/flows/macro-timeline/data")
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "Withheld: no cited source yet"
    assert data["datapoints"] == []
    assert data["historical_precedents"] == []


def test_web_flows_view_html():
    response = client.get("/flows?zip=55401&scenario=grocery_produce&spend=100")
    assert response.status_code == 200
    html = response.text
    assert "The Dollar Flow Map" in html
    assert "Interactive Geographic Map" in html
    assert "Option A: Conventional Supply Chain" in html
    assert "Total Financial Allocation" in html
    assert "Methodology & Data Integrity" in html
    assert "Illustrative model. Output is not a measurement." in html
    assert "Withheld: no cited source yet" in html
    assert "Farm-Gate Audit: What Does the Farmer Actually Pocket?" in html


def test_web_flows_view_drops_unsourced_content():
    response = client.get("/flows?zip=55401&scenario=grocery_produce&spend=100")
    assert response.status_code == 200
    html = response.text
    removed_phrases = [
        "VERIFIED",
        "CAPTIVE",
        "Capital Flight:",
        "Wall Street",
        "Red Pins: Corporate Headquarters",
        "100% of profit",
        "peer-reviewed",
        "almost exclusively",
        "Financial Accounts prove",
        "every single cent",
        "USDA Economic Research Service",
        "SEC Form 10-K Filings",
        "National Co+op Grocers",
        "Packers & Stockyards",
        "PitchBook",
        "FDIC &amp; Federal Reserve",
        "macroData",
        "selectMacroYear",
        "Glass-Steagall",
        "iShares",
        "Big Three",
        "$24 Trillion",
        "85¢",
        "11.8¢",
        "14.5¢",
        "Standard Oil",
        "Gracchi",
    ]
    for phrase in removed_phrases:
        assert phrase not in html, phrase


def test_web_flows_view_has_no_zero_model_rows():
    for scenario_id in ALL_SCENARIO_IDS:
        response = client.get(f"/flows?zip=55401&scenario={scenario_id}&spend=100")
        assert response.status_code == 200
        assert "$0.00 (0.0%)" not in response.text, scenario_id
        assert "Wall Street &amp; PE Extraction" not in response.text, scenario_id


@pytest.mark.parametrize("scenario_id", ALL_SCENARIO_IDS)
def test_web_flows_view_renders_every_scenario(scenario_id):
    response = client.get(f"/flows?zip=60601&scenario={scenario_id}&spend=150")
    assert response.status_code == 200
    assert "Illustrative model. Output is not a measurement." in response.text
    assert "Payee category:" in response.text
