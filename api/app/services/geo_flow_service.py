import math
from typing import Dict, List, Optional, Tuple
from api.app.schemas.domain import (
    GeoFlowNode,
    GeoFlowBranch,
    GeoFlowScenarioSummary,
    GeoFlowTraceResponse,
    FarmGateAudit,
    FarmGateCostItem,
)

# Illustrative location centroids. These are metro and agricultural places used only as
# modeled locations for payee categories. None of them is the headquarters or facility of a
# named company, and no payee in this model is a named company.
KNOWN_ZIPS: Dict[str, Dict[str, any]] = {
    # Twin Cities & MN Agriculture
    "55401": {"city": "Minneapolis", "state": "MN", "lat": 44.9818, "lon": -93.2687},
    "55407": {"city": "Minneapolis", "state": "MN", "lat": 44.9352, "lon": -93.2568},
    "55415": {"city": "Minneapolis", "state": "MN", "lat": 44.9742, "lon": -93.2575},
    "55419": {"city": "Minneapolis", "state": "MN", "lat": 44.9026, "lon": -93.2842},
    "55104": {"city": "St. Paul", "state": "MN", "lat": 44.9556, "lon": -93.1612},
    "55107": {"city": "St. Paul", "state": "MN", "lat": 44.9421, "lon": -93.0825},
    "55370": {"city": "Plato", "state": "MN", "lat": 44.7733, "lon": -94.0416},
    "55350": {"city": "Hutchinson", "state": "MN", "lat": 44.8883, "lon": -94.3683},
    "54665": {"city": "Viroqua", "state": "WI", "lat": 43.5558, "lon": -90.8885},
    # Metro and agricultural-region locations
    "10001": {"city": "New York", "state": "NY", "lat": 40.7501, "lon": -73.9996},
    "68102": {"city": "Omaha", "state": "NE", "lat": 41.2565, "lon": -95.9345},
    "60601": {"city": "Chicago", "state": "IL", "lat": 41.8860, "lon": -87.6225},
    "72701": {"city": "Fayetteville", "state": "AR", "lat": 36.0626, "lon": -94.1574},
    "94104": {"city": "San Francisco", "state": "CA", "lat": 37.7915, "lon": -122.4019},
    "98109": {"city": "Seattle", "state": "WA", "lat": 47.6253, "lon": -122.3477},
    "90012": {"city": "Los Angeles", "state": "CA", "lat": 34.0625, "lon": -118.2386},
    "78701": {"city": "Austin", "state": "TX", "lat": 30.2711, "lon": -97.7437},
    "27516": {"city": "Chapel Hill", "state": "NC", "lat": 35.9132, "lon": -79.0558},
    "29685": {"city": "Sunset", "state": "SC", "lat": 34.9818, "lon": -82.8137},
}

# 3-digit ZIP prefix fallback table to support any 5-digit US ZIP code
ZIP3_FALLBACK: Dict[str, Dict[str, any]] = {
    "0": {"city": "Boston Region", "state": "MA", "lat": 42.3601, "lon": -71.0589},
    "1": {"city": "New York / PA Region", "state": "NY", "lat": 40.7128, "lon": -74.0060},
    "2": {"city": "Mid-Atlantic Region", "state": "VA", "lat": 37.5407, "lon": -77.4360},
    "3": {"city": "Southeast Region", "state": "GA", "lat": 33.7490, "lon": -84.3880},
    "4": {"city": "Great Lakes Region", "state": "OH", "lat": 41.4993, "lon": -81.6944},
    "5": {"city": "Upper Midwest Region", "state": "MN", "lat": 44.9778, "lon": -93.2650},
    "6": {"city": "Midwest Plains", "state": "IL", "lat": 41.8781, "lon": -87.6298},
    "7": {"city": "South Central Region", "state": "TX", "lat": 32.7767, "lon": -96.7970},
    "8": {"city": "Mountain West", "state": "CO", "lat": 39.7392, "lon": -104.9903},
    "9": {"city": "Pacific Coast", "state": "CA", "lat": 34.0522, "lon": -118.2437},
}

# Leak categories used by the model:
#   local_community     - payee category assigned to the local area
#   corporate_overhead  - payee category assigned to corporate or out-of-area overhead
#   shareholder_return  - payee category assigned to shareholder payouts
OUT_OF_AREA_LEAKS = ("corporate_overhead", "shareholder_return")


def resolve_zip(zip_code: str) -> Dict[str, any]:
    """Resolves a 5-digit US ZIP code to city, state, and lat/lon coordinates."""
    clean_zip = str(zip_code).strip()[:5].zfill(5)
    if clean_zip in KNOWN_ZIPS:
        info = KNOWN_ZIPS[clean_zip]
        return {
            "zip": clean_zip,
            "city": info["city"],
            "state": info["state"],
            "lat": info["lat"],
            "lon": info["lon"],
        }

    first_digit = clean_zip[0]
    fallback = ZIP3_FALLBACK.get(first_digit, ZIP3_FALLBACK["5"])
    return {
        "zip": clean_zip,
        "city": fallback["city"],
        "state": fallback["state"],
        "lat": fallback["lat"],
        "lon": fallback["lon"],
    }


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two points in statute miles."""
    r = 3958.8  # Earth radius in miles
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(r * c, 1)


SCENARIOS_META = [
    GeoFlowScenarioSummary(
        id="grocery_produce",
        name="Grocery & Fresh Produce",
        category="Grocery",
        description="Illustrative comparison of a conventional supermarket supply chain with a food co-op and community-farm model.",
    ),
    GeoFlowScenarioSummary(
        id="meat_poultry",
        name="Meat & Poultry",
        category="Food & Meat",
        description="Illustrative comparison of a contract-grower poultry model with a pasture-raised family-farm model.",
    ),
    GeoFlowScenarioSummary(
        id="banking_services",
        name="Banking & Financial Services",
        category="Banking",
        description="Illustrative comparison of where a bank-account dollar is modeled to go: a large-bank model versus a member-owned credit union.",
    ),
    GeoFlowScenarioSummary(
        id="home_services",
        name="Home Trade Services (HVAC/Plumbing)",
        category="Local Services",
        description="Illustrative comparison of a multi-location service-company model with a locally owned independent trade.",
    ),
]


def _insight(prefix: str, conv_defs: List[dict], alt_defs: List[dict]) -> str:
    """Builds the comparison sentence from the scenario's own assumed shares."""
    conv_out = sum(nd["share"] for nd in conv_defs if nd.get("leak_cat") in OUT_OF_AREA_LEAKS) * 100.0
    alt_local = sum(nd["share"] for nd in alt_defs if nd.get("leak_cat") == "local_community") * 100.0
    return (
        f"{prefix} {conv_out:.1f}% of the conventional dollar is assigned to corporate-overhead or "
        f"shareholder-return categories, and {alt_local:.1f}% of the community dollar is assigned to "
        f"local categories. These are assumed shares, not measurements."
    )


def build_scenario_data(
    scenario_id: str,
    origin_info: Dict[str, any],
    spend_amount: float,
) -> Tuple[str, str, List[dict], List[dict], str]:
    """Returns (title, category, conventional_node_defs, alternative_node_defs, comparison_insight)

    Every payee is a category (for example "Contract grower (category)"). No company is named.
    Locations are illustrative metro or regional centroids. Shares are assumptions.
    """
    oz = origin_info["zip"]
    ostate = origin_info["state"]

    if scenario_id == "meat_poultry":
        title = "Meat & Poultry: Contract-Grower Model vs. Pasture-Raised Family Farm (Illustrative)"
        conv_nodes = [
            {
                "role": "Contract-grower farm gate (illustrative)",
                "payee_name": "Contract grower (category)",
                "zip": "72701",
                "share": 0.112,
                "leak_cat": "corporate_overhead",
                "func_cat": "worker_farmer",
                "farm_tier": "contract_grower",
                "farm_notes": "Illustrative assumption: the grower operates under a contract that sets birds, feed and pricing, and carries the facility debt.",
            },
            {
                "role": "Retail meat counter & cashiers",
                "payee_name": "Retail store hourly staff (category)",
                "zip": oz,
                "share": 0.120,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Processing plant line work",
                "payee_name": "Processing plant hourly staff (category)",
                "zip": "68102",
                "share": 0.128,
                "leak_cat": "corporate_overhead",
                "func_cat": "worker_farmer",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Cold-chain transport & packaging",
                "payee_name": "Refrigerated transport and packaging (category)",
                "zip": "60601",
                "share": 0.180,
                "leak_cat": "corporate_overhead",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Processor margin (feed, processing, branding)",
                "payee_name": "Processor margin (category)",
                "zip": "72701",
                "share": 0.160,
                "leak_cat": "corporate_overhead",
                "func_cat": "executive_shareholder",
                "farm_tier": "corporate_agribusiness",
                "farm_notes": "Illustrative assumption: the processor keeps the largest margin on feed milling, processing and branding.",
            },
            {
                "role": "Retail headquarters margin",
                "payee_name": "Retail headquarters (category)",
                "zip": "10001",
                "share": 0.150,
                "leak_cat": "corporate_overhead",
                "func_cat": "executive_shareholder",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Shareholder dividends & buybacks",
                "payee_name": "Shareholder returns (category)",
                "zip": "10001",
                "share": 0.150,
                "leak_cat": "shareholder_return",
                "func_cat": "executive_shareholder",
                "farm_tier": None,
                "farm_notes": None,
            },
        ]
        alt_nodes = [
            {
                "role": "Pasture-raised family farm gate",
                "payee_name": "Independent family farm (category)",
                "zip": "55370" if ostate == "MN" else oz,
                "share": 0.720,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": "community_farmer",
                "farm_notes": "Illustrative assumption: an owner-operator using rotational pasture grazing and setting direct sales prices.",
            },
            {
                "role": "Small-batch processing",
                "payee_name": "Local small-batch processor (category)",
                "zip": "55350" if ostate == "MN" else oz,
                "share": 0.160,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Local delivery & farm-stand staff",
                "payee_name": "Local delivery and stand staff (category)",
                "zip": oz,
                "share": 0.080,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Soil and pasture reinvestment",
                "payee_name": "Farm soil-health reinvestment (category)",
                "zip": "55370" if ostate == "MN" else oz,
                "share": 0.040,
                "leak_cat": "local_community",
                "func_cat": "operations",
                "farm_tier": "community_farmer",
                "farm_notes": "Illustrative assumption: reinvested in pasture and soil biology.",
            },
        ]
        prefix = "In this illustrative poultry model,"

    elif scenario_id == "banking_services":
        title = "Banking: Large-Bank Model vs. Member-Owned Credit Union (Illustrative)"
        conv_nodes = [
            {
                "role": "Branch staff (cashiers & tellers)",
                "payee_name": "Branch staff, hourly (category)",
                "zip": oz,
                "share": 0.140,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Central operations & compliance",
                "payee_name": "Central operations and compliance (category)",
                "zip": "60601",
                "share": 0.100,
                "leak_cat": "corporate_overhead",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Trading & derivatives operations",
                "payee_name": "Trading and derivatives operations (category)",
                "zip": "10001",
                "share": 0.220,
                "leak_cat": "corporate_overhead",
                "func_cat": "executive_shareholder",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Executive compensation",
                "payee_name": "Executive compensation (category)",
                "zip": "94104",
                "share": 0.125,
                "leak_cat": "corporate_overhead",
                "func_cat": "executive_shareholder",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Buybacks & dividends to investors",
                "payee_name": "Institutional investors: buybacks and dividends (category)",
                "zip": "10001",
                "share": 0.415,
                "leak_cat": "shareholder_return",
                "func_cat": "executive_shareholder",
                "farm_tier": None,
                "farm_notes": None,
            },
        ]
        alt_nodes = [
            {
                "role": "Member dividends & deposit yield",
                "payee_name": "Member dividends and deposit yield (category)",
                "zip": oz,
                "share": 0.380,
                "leak_cat": "local_community",
                "func_cat": "member_dividends",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Loan officers & tellers",
                "payee_name": "Member-owned credit union staff (category)",
                "zip": "55107" if ostate == "MN" else oz,
                "share": 0.340,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Local small-business & farm lending",
                "payee_name": "Local small-business and farm lending (category)",
                "zip": oz,
                "share": 0.200,
                "leak_cat": "local_community",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Community education & youth grants",
                "payee_name": "Community education grants (category)",
                "zip": oz,
                "share": 0.080,
                "leak_cat": "local_community",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
        ]
        prefix = "In this illustrative banking model,"

    elif scenario_id == "home_services":
        title = "Home Services: Multi-Location Company Model vs. Local Independent Trade (Illustrative)"
        conv_nodes = [
            {
                "role": "Field technician wages",
                "payee_name": "Field technician, hourly (category)",
                "zip": oz,
                "share": 0.220,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Centralized dispatch & call center",
                "payee_name": "Centralized dispatch and overhead (category)",
                "zip": "90012",
                "share": 0.220,
                "leak_cat": "corporate_overhead",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Software & fleet leases",
                "payee_name": "Software and fleet vendor (category)",
                "zip": "78701",
                "share": 0.180,
                "leak_cat": "corporate_overhead",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Management fees & acquisition-debt service",
                "payee_name": "Management fees and debt service (category)",
                "zip": "10001",
                "share": 0.380,
                "leak_cat": "shareholder_return",
                "func_cat": "executive_shareholder",
                "farm_tier": None,
                "farm_notes": None,
            },
        ]
        alt_nodes = [
            {
                "role": "Owner-operator journeyman",
                "payee_name": "Locally licensed owner-operator (category)",
                "zip": oz,
                "share": 0.580,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Apprentice & helper wages",
                "payee_name": "Local trade apprentice (category)",
                "zip": oz,
                "share": 0.240,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Local supply purchases",
                "payee_name": "Local supply vendor (category)",
                "zip": oz,
                "share": 0.140,
                "leak_cat": "local_community",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Local tool & van reinvestment",
                "payee_name": "Local equipment reinvestment (category)",
                "zip": oz,
                "share": 0.040,
                "leak_cat": "local_community",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
        ]
        prefix = "In this illustrative home-services model,"

    else:  # default: grocery_produce
        title = "Grocery: Conventional Supermarket Chain vs. Food Co-op & Community Farm (Illustrative)"
        conv_nodes = [
            {
                "role": "Contract farm gate",
                "payee_name": "Contract farm grower (category)",
                "zip": "72701",
                "share": 0.147,
                "leak_cat": "corporate_overhead",
                "func_cat": "worker_farmer",
                "farm_tier": "contract_grower",
                "farm_notes": "Illustrative assumption: the grower sells under a contract to an agribusiness buyer and is exposed to commodity prices. Land may be leased.",
            },
            {
                "role": "Store workers & cashiers",
                "payee_name": "Store staff, hourly (category)",
                "zip": oz,
                "share": 0.125,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Processing, transport & packaging",
                "payee_name": "Food processing and packaging (category)",
                "zip": "55419",
                "share": 0.283,
                "leak_cat": "corporate_overhead",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Brand marketing & advertising",
                "payee_name": "Advertising and marketing services (category)",
                "zip": "10001",
                "share": 0.085,
                "leak_cat": "corporate_overhead",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Store real-estate lease",
                "payee_name": "Commercial property owner (category)",
                "zip": "90012",
                "share": 0.160,
                "leak_cat": "corporate_overhead",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Retail executive compensation",
                "payee_name": "Retail executive compensation (category)",
                "zip": "94104",
                "share": 0.042,
                "leak_cat": "corporate_overhead",
                "func_cat": "executive_shareholder",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Shareholder buybacks & dividends",
                "payee_name": "Institutional investors: buybacks and dividends (category)",
                "zip": "10001",
                "share": 0.158,
                "leak_cat": "shareholder_return",
                "func_cat": "executive_shareholder",
                "farm_tier": None,
                "farm_notes": None,
            },
        ]
        alt_nodes = [
            {
                "role": "Independent community farm gate",
                "payee_name": "Independent family farm (category)",
                "zip": "55370" if ostate == "MN" else oz,
                "share": 0.420,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": "community_farmer",
                "farm_notes": "Illustrative assumption: a regenerative family farm selling direct or through a regional co-op.",
            },
            {
                "role": "Co-op staff, living wage",
                "payee_name": "Food co-op staff (category)",
                "zip": "55407" if ostate == "MN" else oz,
                "share": 0.285,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Regional logistics & cold storage",
                "payee_name": "Regional food hub and cold storage (category)",
                "zip": "55415" if ostate == "MN" else oz,
                "share": 0.180,
                "leak_cat": "local_community",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Member patronage rebates",
                "payee_name": "Member rebates (category)",
                "zip": oz,
                "share": 0.065,
                "leak_cat": "local_community",
                "func_cat": "member_dividends",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Community food-access grants",
                "payee_name": "Community food-access grants (category)",
                "zip": oz,
                "share": 0.050,
                "leak_cat": "local_community",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
        ]
        prefix = "In this illustrative grocery model,"

    insight = _insight(prefix, conv_nodes, alt_nodes)
    return title, scenario_id, conv_nodes, alt_nodes, insight


def get_farm_gate_decomposition(
    scenario_id: str,
    farm_tier: str,
    farm_gate_amount: float,
) -> Optional[FarmGateAudit]:
    """Splits a farm-gate payment into assumed input and land shares and a modeled residual.

    All shares are illustrative assumptions entered in code. They are not measurements,
    and the beneficiary entries are categories, not named companies.
    """
    if farm_gate_amount <= 0:
        return None

    if scenario_id == "grocery_produce":
        if farm_tier == "contract_grower":
            # Assumed row-crop / produce cost structure (illustrative)
            rent = round(0.280 * farm_gate_amount, 2)
            fert = round(0.210 * farm_gate_amount, 2)
            mach = round(0.180 * farm_gate_amount, 2)
            seed = round(0.125 * farm_gate_amount, 2)
            chem = round(0.085 * farm_gate_amount, 2)
            fin = round(0.050 * farm_gate_amount, 2)
            expenses_sum = round(rent + fert + mach + seed + chem + fin, 2)
            net_income = round(farm_gate_amount - expenses_sum, 2)
            net_pct = round((net_income / farm_gate_amount) * 100.0, 1)

            return FarmGateAudit(
                farm_type="contract_grower",
                title="Illustrative Conventional Farm-Gate Model (assumed shares)",
                gross_farm_gate_amount=farm_gate_amount,
                input_expenses=[
                    FarmGateCostItem(
                        name="Cash Rent & Land Mortgage",
                        amount=rent,
                        percentage_of_farm_gate=28.0,
                        corporate_beneficiaries=["Non-operator landlords (category)", "Farmland investors (category)", "Agricultural lenders (category)"],
                        color_code="#94a3b8",
                    ),
                    FarmGateCostItem(
                        name="Synthetic Fertilizer (NPK)",
                        amount=fert,
                        percentage_of_farm_gate=21.0,
                        corporate_beneficiaries=["Fertilizer manufacturers (category)"],
                        color_code="#f59e0b",
                    ),
                    FarmGateCostItem(
                        name="Machinery Depreciation, Tech & Fuel",
                        amount=mach,
                        percentage_of_farm_gate=18.0,
                        corporate_beneficiaries=["Equipment manufacturers (category)", "Fuel suppliers (category)"],
                        color_code="#64748b",
                    ),
                    FarmGateCostItem(
                        name="Patented Seed",
                        amount=seed,
                        percentage_of_farm_gate=12.5,
                        corporate_beneficiaries=["Patented seed suppliers (category)"],
                        color_code="#dc2626",
                    ),
                    FarmGateCostItem(
                        name="Crop Protection (Herbicides/Pesticides)",
                        amount=chem,
                        percentage_of_farm_gate=8.5,
                        corporate_beneficiaries=["Crop protection suppliers (category)"],
                        color_code="#ea580c",
                    ),
                    FarmGateCostItem(
                        name="Operating Loan Interest & Crop Insurance",
                        amount=fin,
                        percentage_of_farm_gate=5.0,
                        corporate_beneficiaries=["Agricultural lenders (category)", "Crop insurance (category)"],
                        color_code="#6b7280",
                    ),
                    FarmGateCostItem(
                        name="Net Farmer Take-Home (illustrative residual)",
                        amount=net_income,
                        percentage_of_farm_gate=net_pct,
                        corporate_beneficiaries=["Farmer household (category)"],
                        is_farmer_take_home=True,
                        color_code="#10b981",
                    ),
                ],
                net_farmer_take_home_amount=net_income,
                net_farmer_take_home_pct=net_pct,
                notes=(
                    f"Illustrative assumption: in this model, input and land costs take most of the farm-gate payment, "
                    f"leaving the grower a modeled residual of {net_pct:.1f}%. These are assumed shares, not measurements."
                ),
            )

        elif farm_tier == "community_farmer":
            # Assumed community / regenerative model (illustrative)
            crew = round(0.650 * farm_gate_amount, 2)
            soil = round(0.100 * farm_gate_amount, 2)
            equip = round(0.150 * farm_gate_amount, 2)
            land = round(farm_gate_amount - (crew + soil + equip), 2)
            land_pct = round((land / farm_gate_amount) * 100.0, 1)

            return FarmGateAudit(
                farm_type="community_farmer",
                title="Illustrative Independent Community Farm-Gate Model (assumed shares)",
                gross_farm_gate_amount=farm_gate_amount,
                input_expenses=[
                    FarmGateCostItem(
                        name="Living-Wage Farmer & Crew Living Return",
                        amount=crew,
                        percentage_of_farm_gate=65.0,
                        corporate_beneficiaries=["Independent family farmer (category)", "Farm crew (category)"],
                        is_farmer_take_home=True,
                        color_code="#10b981",
                    ),
                    FarmGateCostItem(
                        name="Equipment Care & Renewable Energy",
                        amount=equip,
                        percentage_of_farm_gate=15.0,
                        corporate_beneficiaries=["Local equipment repair (category)", "Local energy providers (category)"],
                        color_code="#34d399",
                    ),
                    FarmGateCostItem(
                        name="Soil Health, Cover Crops & Organic Seed",
                        amount=soil,
                        percentage_of_farm_gate=10.0,
                        corporate_beneficiaries=["Organic seed suppliers (category)", "Cover-crop suppliers (category)"],
                        color_code="#059669",
                    ),
                    FarmGateCostItem(
                        name="Land Stewardship & Conservation Reserve",
                        amount=land,
                        percentage_of_farm_gate=land_pct,
                        corporate_beneficiaries=["Land trust or conservation fund (category)"],
                        color_code="#0d9488",
                    ),
                ],
                net_farmer_take_home_amount=crew,
                net_farmer_take_home_pct=65.0,
                notes=(
                    "Illustrative assumption: in this model the farm family and crew keep 65% of the farm-gate payment "
                    "as living return, with no purchased patented inputs and direct or cooperative sales. "
                    "These are assumed shares, not measurements."
                ),
            )

    elif scenario_id == "meat_poultry":
        if farm_tier == "contract_grower":
            # Assumed contract-grower model (illustrative)
            debt = round(0.450 * farm_gate_amount, 2)
            heat = round(0.230 * farm_gate_amount, 2)
            repairs = round(0.170 * farm_gate_amount, 2)
            net_income = round(farm_gate_amount - (debt + heat + repairs), 2)
            net_pct = round((net_income / farm_gate_amount) * 100.0, 1)

            return FarmGateAudit(
                farm_type="contract_grower",
                title="Illustrative Contract-Grower Model (assumed shares)",
                gross_farm_gate_amount=farm_gate_amount,
                input_expenses=[
                    FarmGateCostItem(
                        name="Debt Service on Facilities (illustrative)",
                        amount=debt,
                        percentage_of_farm_gate=45.0,
                        corporate_beneficiaries=["Agricultural lenders (category)", "Small-business lenders (category)"],
                        color_code="#94a3b8",
                    ),
                    FarmGateCostItem(
                        name="Electricity & Heating Fuel (ventilation and heating)",
                        amount=heat,
                        percentage_of_farm_gate=23.0,
                        corporate_beneficiaries=["Utilities (category)", "Fuel distributors (category)"],
                        color_code="#f59e0b",
                    ),
                    FarmGateCostItem(
                        name="Facility Maintenance, Bedding & Repairs",
                        amount=repairs,
                        percentage_of_farm_gate=17.0,
                        corporate_beneficiaries=["Ventilation equipment dealers (category)", "Bedding suppliers (category)"],
                        color_code="#64748b",
                    ),
                    FarmGateCostItem(
                        name="Contract Grower Net Take-Home Pay (illustrative residual)",
                        amount=net_income,
                        percentage_of_farm_gate=net_pct,
                        corporate_beneficiaries=["Grower household (category)"],
                        is_farmer_take_home=True,
                        color_code="#10b981",
                    ),
                ],
                net_farmer_take_home_amount=net_income,
                net_farmer_take_home_pct=net_pct,
                notes=(
                    f"Illustrative assumption: under the contract model assumed here, the integrator sets birds, feed and pricing, "
                    f"and the grower carries facility debt and operating costs. Modeled residual: {net_pct:.1f}% of the farm payment. "
                    f"These are assumed shares, not measurements."
                ),
            )

        elif farm_tier == "community_farmer":
            # Assumed pasture-raised family-farm model (illustrative)
            steward = round(0.700 * farm_gate_amount, 2)
            pasture = round(0.120 * farm_gate_amount, 2)
            fencing = round(0.100 * farm_gate_amount, 2)
            vet = round(farm_gate_amount - (steward + pasture + fencing), 2)
            vet_pct = round((vet / farm_gate_amount) * 100.0, 1)

            return FarmGateAudit(
                farm_type="community_farmer",
                title="Illustrative Pasture-Raised Family Farm Model (assumed shares)",
                gross_farm_gate_amount=farm_gate_amount,
                input_expenses=[
                    FarmGateCostItem(
                        name="Pasture Steward Living Family Return",
                        amount=steward,
                        percentage_of_farm_gate=70.0,
                        corporate_beneficiaries=["Family farm owner-operator (category)"],
                        is_farmer_take_home=True,
                        color_code="#10b981",
                    ),
                    FarmGateCostItem(
                        name="Rotational Pasture Seeding & Soil Health",
                        amount=pasture,
                        percentage_of_farm_gate=12.0,
                        corporate_beneficiaries=["Forage and soil-biology suppliers (category)"],
                        color_code="#059669",
                    ),
                    FarmGateCostItem(
                        name="Mobile Fencing, Water Infrastructure & Trailers",
                        amount=fencing,
                        percentage_of_farm_gate=10.0,
                        corporate_beneficiaries=["Local hardware and equipment fabricators (category)"],
                        color_code="#34d399",
                    ),
                    FarmGateCostItem(
                        name="Animal Care & Minerals",
                        amount=vet,
                        percentage_of_farm_gate=vet_pct,
                        corporate_beneficiaries=["Veterinary and mineral suppliers (category)"],
                        color_code="#0d9488",
                    ),
                ],
                net_farmer_take_home_amount=steward,
                net_farmer_take_home_pct=70.0,
                notes=(
                    "Illustrative assumption: in this model the owner-operator sets direct-to-consumer prices and keeps 70% "
                    "of the farm payment as family earnings. These are assumed shares, not measurements."
                ),
            )

    return None


def compute_branch(
    option_type: str,
    display_title: str,
    node_defs: List[dict],
    origin_info: Dict[str, any],
    spend_amount: float,
    summary_text: str,
    scenario_id: str = "grocery_produce",
) -> GeoFlowBranch:
    """Computes calculated nodes, distances, worker share, operations, and out-of-area amounts.

    Field names such as capital_flight_amount are kept for API compatibility. In the output
    they are the modeled amount assigned outside the local area.
    """
    olat = origin_info["lat"]
    olon = origin_info["lon"]

    nodes: List[GeoFlowNode] = []
    total_local = 0.0
    total_flight = 0.0
    total_worker_farmer = 0.0
    total_operations = 0.0
    total_exec_shareholder = 0.0
    total_member_dividends = 0.0
    weighted_distance = 0.0

    for nd in node_defs:
        dest_zip = nd["zip"]
        dest_info = resolve_zip(dest_zip)
        dist = haversine_miles(olat, olon, dest_info["lat"], dest_info["lon"])
        pct = nd["share"] * 100.0
        node_amount = round(nd["share"] * spend_amount, 2)

        # A node is ONLY local if within regional distance AND categorized as local_community
        is_local = (dist <= 60.0 or dest_zip == origin_info["zip"]) and nd.get("leak_cat") == "local_community"

        if is_local:
            total_local += node_amount
        else:
            total_flight += node_amount

        # Functional classification
        fcat = nd.get("func_cat", "operations")
        if fcat == "worker_farmer":
            total_worker_farmer += node_amount
        elif fcat == "operations":
            total_operations += node_amount
        elif fcat == "member_dividends":
            total_member_dividends += node_amount
        elif fcat == "executive_shareholder":
            total_exec_shareholder += node_amount

        weighted_distance += dist * (nd["share"])

        farm_audit = None
        if nd.get("farm_tier") in ["contract_grower", "community_farmer"]:
            farm_audit = get_farm_gate_decomposition(
                scenario_id=scenario_id,
                farm_tier=nd["farm_tier"],
                farm_gate_amount=node_amount,
            )

        nodes.append(
            GeoFlowNode(
                role=nd["role"],
                payee_name=nd["payee_name"],
                destination_zip=dest_zip,
                city=dest_info["city"],
                state=dest_info["state"],
                lat=dest_info["lat"],
                lon=dest_info["lon"],
                amount=node_amount,
                percentage=round(pct, 1),
                distance_miles=dist,
                is_local=is_local,
                leak_category=nd["leak_cat"],
                farm_ownership_tier=nd.get("farm_tier"),
                farm_ownership_notes=nd.get("farm_notes"),
                farm_gate_audit=farm_audit,
            )
        )

    # Ensure node amounts sum exactly to spend_amount
    nodes_amount_sum = round(sum(n.amount for n in nodes), 2)
    if spend_amount > 0 and nodes_amount_sum != round(spend_amount, 2) and len(nodes) > 0:
        node_diff = round(spend_amount - nodes_amount_sum, 2)
        nodes[-1].amount = round(nodes[-1].amount + node_diff, 2)

    # Ensure total amounts balance exactly to spend_amount
    functional_sum = total_worker_farmer + total_operations + total_exec_shareholder + total_member_dividends
    if spend_amount > 0 and round(functional_sum, 2) != round(spend_amount, 2):
        diff = round(spend_amount - functional_sum, 2)
        total_operations = round(total_operations + diff, 2)

    geo_sum = total_local + total_flight
    if spend_amount > 0 and round(geo_sum, 2) != round(spend_amount, 2):
        diff_geo = round(spend_amount - geo_sum, 2)
        total_flight = round(total_flight + diff_geo, 2)

    local_pct = round((total_local / spend_amount) * 100.0, 1) if spend_amount > 0 else 0.0
    flight_pct = round(100.0 - local_pct, 1) if spend_amount > 0 else 0.0

    wf_pct = round((total_worker_farmer / spend_amount) * 100.0, 1) if spend_amount > 0 else 0.0
    ops_pct = round((total_operations / spend_amount) * 100.0, 1) if spend_amount > 0 else 0.0
    es_pct = round((total_exec_shareholder / spend_amount) * 100.0, 1) if spend_amount > 0 else 0.0
    mem_pct = round((total_member_dividends / spend_amount) * 100.0, 1) if spend_amount > 0 else 0.0

    # Ensure functional percentages add up to exactly 100.0%
    if spend_amount > 0:
        pct_sum = round(wf_pct + ops_pct + es_pct + mem_pct, 1)
        if pct_sum != 100.0:
            diff_pct = round(100.0 - pct_sum, 1)
            ops_pct = round(ops_pct + diff_pct, 1)

    return GeoFlowBranch(
        option_type=option_type,
        display_title=display_title,
        nodes=nodes,
        total_spend=spend_amount,
        local_retained_amount=round(total_local, 2),
        local_retained_pct=local_pct,
        capital_flight_amount=round(total_flight, 2),
        capital_flight_pct=flight_pct,
        worker_farmer_amount=round(total_worker_farmer, 2),
        worker_farmer_pct=wf_pct,
        operations_logistics_amount=round(total_operations, 2),
        operations_logistics_pct=ops_pct,
        executive_shareholder_amount=round(total_exec_shareholder, 2),
        executive_shareholder_pct=es_pct,
        member_dividends_amount=round(total_member_dividends, 2),
        member_dividends_pct=mem_pct,
        avg_miles_traveled=round(weighted_distance, 1),
        summary_text=summary_text,
    )


def trace_dollar_flow(
    origin_zip: str = "55401",
    scenario_id: str = "grocery_produce",
    spend_amount: float = 100.0,
) -> GeoFlowTraceResponse:
    """Computes an illustrative side-by-side dollar routing trace based on the origin ZIP.

    Payees are category-level labels only. Shares and locations are assumptions, not measurements.
    """
    origin_info = resolve_zip(origin_zip)
    title, cat, conv_defs, alt_defs, insight = build_scenario_data(
        scenario_id, origin_info, spend_amount
    )

    conv_branch = compute_branch(
        option_type="conventional",
        display_title="Conventional Supply Chain (illustrative)",
        node_defs=conv_defs,
        origin_info=origin_info,
        spend_amount=spend_amount,
        summary_text="Illustrative model. Shares are assumptions, not measurements, and each payee is a category rather than a named company.",
        scenario_id=scenario_id,
    )

    alt_branch = compute_branch(
        option_type="alternative",
        display_title="Community Farm & Local Co-op Alternative (illustrative)",
        node_defs=alt_defs,
        origin_info=origin_info,
        spend_amount=spend_amount,
        summary_text="Illustrative model. Shares are assumptions, not measurements. The alternative assigns its shares to local categories and member rebates.",
        scenario_id=scenario_id,
    )

    return GeoFlowTraceResponse(
        origin_zip=origin_info["zip"],
        origin_city=origin_info["city"],
        origin_state=origin_info["state"],
        origin_lat=origin_info["lat"],
        origin_lon=origin_info["lon"],
        spend_amount=spend_amount,
        scenario_id=scenario_id,
        scenario_title=title,
        conventional=conv_branch,
        alternative=alt_branch,
        comparison_insight=insight,
    )
