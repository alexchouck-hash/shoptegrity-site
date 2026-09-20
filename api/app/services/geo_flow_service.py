import math
from typing import Dict, List, Optional, Tuple
from api.app.schemas.domain import (
    GeoFlowNode,
    GeoFlowBranch,
    GeoFlowScenarioSummary,
    GeoFlowTraceResponse,
)

# Representative ZIP centroids across key metros, agricultural hubs, and corporate/financial centers
KNOWN_ZIPS: Dict[str, Dict[str, any]] = {
    # Twin Cities & MN Agriculture
    "55401": {"city": "Minneapolis", "state": "MN", "lat": 44.9818, "lon": -93.2687},
    "55407": {"city": "Minneapolis", "state": "MN", "lat": 44.9352, "lon": -93.2568},
    "55415": {"city": "Minneapolis", "state": "MN", "lat": 44.9742, "lon": -93.2575},
    "55419": {"city": "Minneapolis", "state": "MN", "lat": 44.9026, "lon": -93.2842},
    "55426": {"city": "Golden Valley", "state": "MN", "lat": 44.9877, "lon": -93.3762},
    "55104": {"city": "St. Paul", "state": "MN", "lat": 44.9556, "lon": -93.1612},
    "55107": {"city": "St. Paul", "state": "MN", "lat": 44.9421, "lon": -93.0825},
    "55370": {"city": "Plato", "state": "MN", "lat": 44.7733, "lon": -94.0416},
    "55350": {"city": "Hutchinson", "state": "MN", "lat": 44.8883, "lon": -94.3683},
    "54665": {"city": "Viroqua", "state": "WI", "lat": 43.5558, "lon": -90.8885},
    # Major Corporate & Financial Centers
    "10001": {"city": "New York", "state": "NY", "lat": 40.7501, "lon": -73.9996},
    "10005": {"city": "New York", "state": "NY", "lat": 40.7064, "lon": -74.0090},
    "10055": {"city": "New York", "state": "NY", "lat": 40.7610, "lon": -73.9740},
    "19355": {"city": "Malvern", "state": "PA", "lat": 40.0362, "lon": -75.5138},
    "19801": {"city": "Wilmington", "state": "DE", "lat": 39.7391, "lon": -75.5398},
    "72716": {"city": "Bentonville", "state": "AR", "lat": 36.3729, "lon": -94.2088},
    "72764": {"city": "Springdale", "state": "AR", "lat": 36.1867, "lon": -94.1288},
    "68102": {"city": "Omaha", "state": "NE", "lat": 41.2565, "lon": -95.9345},
    "60601": {"city": "Chicago", "state": "IL", "lat": 41.8860, "lon": -87.6225},
    "94104": {"city": "San Francisco", "state": "CA", "lat": 37.7915, "lon": -122.4019},
    "98109": {"city": "Seattle", "state": "WA", "lat": 47.6253, "lon": -122.3477},
    "90012": {"city": "Los Angeles", "state": "CA", "lat": 34.0625, "lon": -118.2386},
    "78701": {"city": "Austin", "state": "TX", "lat": 30.2711, "lon": -97.7437},
    "28202": {"city": "Charlotte", "state": "NC", "lat": 35.2271, "lon": -80.8431},
    "29685": {"city": "Sunset", "state": "SC", "lat": 34.9818, "lon": -82.8137},
    "27516": {"city": "Chapel Hill", "state": "NC", "lat": 35.9132, "lon": -79.0558},
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
        description="Contrasts industrial supermarket supply chains with direct community farm and food co-op sourcing.",
    ),
    GeoFlowScenarioSummary(
        id="meat_poultry",
        name="Meat & Poultry",
        category="Food & Meat",
        description="Exposes the corporate integrator poultry model versus pasture-raised independent family growers.",
    ),
    GeoFlowScenarioSummary(
        id="banking_services",
        name="Banking & Financial Services",
        category="Banking",
        description="Tracks consumer banking dollars: Wall Street buyback leakage versus local credit union retention.",
    ),
    GeoFlowScenarioSummary(
        id="home_services",
        name="Home Trade Services (HVAC/Plumbing)",
        category="Local Services",
        description="Shows capital extraction by private equity rollups versus local independent journeyman trades.",
    ),
]


def build_scenario_data(
    scenario_id: str,
    origin_info: Dict[str, any],
    spend_amount: float,
) -> Tuple[str, str, List[dict], List[dict], str]:
    """Returns (title, category, conventional_node_defs, alternative_node_defs, comparison_insight)"""
    oz = origin_info["zip"]
    olat = origin_info["lat"]
    olon = origin_info["lon"]
    ocity = origin_info["city"]
    ostate = origin_info["state"]

    if scenario_id == "meat_poultry":
        title = "Meat & Poultry: Corporate Integrator CAFO vs. Pasture-Raised Family Farm"
        conv_nodes = [
            {
                "role": "Captive Contract Farm Gate",
                "payee_name": "Tyson Contract Grower (Debt-Bound)",
                "zip": "72764",
                "share": 0.112,
                "leak_cat": "corporate_overhead",
                "func_cat": "worker_farmer",
                "farm_tier": "contract_grower",
                "farm_notes": "Nominal family farm, but company owns the birds, feed, and pricing contract; grower carries $1M+ mortgage.",
            },
            {
                "role": "Frontline Supermarket Meat Counter & Cashiers",
                "payee_name": "Supermarket Meat Department Hourly Staff",
                "zip": oz,
                "share": 0.120,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Industrial Meatpacking Line Workers",
                "payee_name": "Processing Plant Line Workers",
                "zip": "68102",
                "share": 0.128,
                "leak_cat": "corporate_overhead",
                "func_cat": "worker_farmer",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Cold Chain Transport & Specialized Packaging",
                "payee_name": "Multinational Logistics Conglomerate",
                "zip": "60601",
                "share": 0.180,
                "leak_cat": "corporate_overhead",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Corporate Integrator Processing Margin",
                "payee_name": "Tyson Foods Corporate Agribusiness",
                "zip": "72764",
                "share": 0.160,
                "leak_cat": "corporate_overhead",
                "func_cat": "executive_shareholder",
                "farm_tier": "corporate_agribusiness",
                "farm_notes": "Integrator captures dominant margin on feed milling, processing, and brand markup.",
            },
            {
                "role": "Supermarket Retail Corporate HQ Margin",
                "payee_name": "Supermarket Corporate Headquarters",
                "zip": "72716",
                "share": 0.150,
                "leak_cat": "corporate_overhead",
                "func_cat": "executive_shareholder",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Wall Street Shareholders & Private Equity",
                "payee_name": "Institutional Dividend & Buyback Pool",
                "zip": "19801",
                "share": 0.150,
                "leak_cat": "wall_street_leak",
                "func_cat": "executive_shareholder",
                "farm_tier": None,
                "farm_notes": None,
            },
        ]
        alt_nodes = [
            {
                "role": "Independent Community Farm Gate",
                "payee_name": "Pasture-Raised Family Steward",
                "zip": "55370" if ostate == "MN" else oz,
                "share": 0.720,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": "community_farmer",
                "farm_notes": "100% Independent owner-operator. Rotational pasture grazing, sets own direct-to-consumer prices.",
            },
            {
                "role": "Artisan USDA Regional Processor",
                "payee_name": "Local Small-Batch Meat Locker",
                "zip": "55350" if ostate == "MN" else oz,
                "share": 0.160,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Local Delivery & Farm Stand Staff",
                "payee_name": "Community Farm Drivers & Handlers",
                "zip": oz,
                "share": 0.080,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Soil Regeneration & Stewardship Reinvestment",
                "payee_name": "Farm Soil Health Capital",
                "zip": "55370" if ostate == "MN" else oz,
                "share": 0.040,
                "leak_cat": "local_community",
                "func_cat": "operations",
                "farm_tier": "community_farmer",
                "farm_notes": "Reinvested directly into multi-species pasture and soil biology.",
            },
        ]
        insight = (
            f"Under the conventional poultry model, only 11.2¢ of each dollar goes to a debt-bound contract grower in Springdale, AR, "
            f"while 50¢ leaks to corporate integrators, supermarket HQs, and Wall Street. "
            f"Buying direct from an independent community farmer keeps 72¢ directly with the soil steward."
        )

    elif scenario_id == "banking_services":
        title = "Banking: Wall Street Megabank vs. Community Credit Union"
        conv_nodes = [
            {
                "role": "Local Branch Cashiers & Tellers",
                "payee_name": "Frontline Metro Branch Workers",
                "zip": oz,
                "share": 0.140,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Corporate Central IT & Compliance",
                "payee_name": "National Operations Hub",
                "zip": "28202",
                "share": 0.100,
                "leak_cat": "corporate_overhead",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Financial Derivatives & Trading Speculation",
                "payee_name": "Delaware Capital Markets Holding Co",
                "zip": "19801",
                "share": 0.220,
                "leak_cat": "wall_street_leak",
                "func_cat": "executive_shareholder",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Executive Compensation & Golden Parachutes",
                "payee_name": "Megabank Executive Committee",
                "zip": "94104",
                "share": 0.125,
                "leak_cat": "corporate_overhead",
                "func_cat": "executive_shareholder",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Wall Street Stock Buybacks & Dividends",
                "payee_name": "Institutional Hedge Funds & Asset Managers",
                "zip": "10005",
                "share": 0.415,
                "leak_cat": "wall_street_leak",
                "func_cat": "executive_shareholder",
                "farm_tier": None,
                "farm_notes": None,
            },
        ]
        alt_nodes = [
            {
                "role": "Member High-Yield Dividend & APY",
                "payee_name": "Member Depositor Account (Returned to You)",
                "zip": oz,
                "share": 0.380,
                "leak_cat": "local_community",
                "func_cat": "member_dividends",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Living Wage Loan Officers & Tellers",
                "payee_name": "Local Member-Owned Credit Union Staff",
                "zip": "55107" if ostate == "MN" else oz,
                "share": 0.340,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Local Small Business & Farm Lending Pool",
                "payee_name": "Community Development Loan Reserve",
                "zip": oz,
                "share": 0.200,
                "leak_cat": "local_community",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Community Education & Youth Grants",
                "payee_name": "Local Cooperative Foundation",
                "zip": oz,
                "share": 0.080,
                "leak_cat": "local_community",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
        ]
        insight = (
            f"Megabanks bleed $76.00 of every $100 spent directly into Wall Street buybacks, golden parachutes, and Delaware derivatives entities. "
            f"A community credit union keeps 100% of capital within the local member ecosystem and regional lending pools."
        )

    elif scenario_id == "home_services":
        title = "Home Services: PE-Owned Rollup Disguised vs. Local Independent Trade"
        conv_nodes = [
            {
                "role": "Frontline Service Technician",
                "payee_name": "Hourly HVAC/Plumbing Tech",
                "zip": oz,
                "share": 0.220,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "National Aggregator Call Center",
                "payee_name": "Centralized Dispatch & Overhead",
                "zip": "90012",
                "share": 0.220,
                "leak_cat": "corporate_overhead",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Proprietary Software & Fleet Lease",
                "payee_name": "Corporate Tech Vendor",
                "zip": "78701",
                "share": 0.180,
                "leak_cat": "corporate_overhead",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Private Equity Management Fees & LBO Debt",
                "payee_name": "Wall Street PE Rollup Platform",
                "zip": "19801",
                "share": 0.380,
                "leak_cat": "wall_street_leak",
                "func_cat": "executive_shareholder",
                "farm_tier": None,
                "farm_notes": None,
            },
        ]
        alt_nodes = [
            {
                "role": "Master Journeyman / Owner-Operator",
                "payee_name": "Local Licensed Trade Owner",
                "zip": oz,
                "share": 0.580,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Apprentice & Local Helper Wages",
                "payee_name": "Local Trade Apprentice",
                "zip": oz,
                "share": 0.240,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Independent Hardware Co-op Supplies",
                "payee_name": "Local Hardware / Plumbing Supply Co-op",
                "zip": oz,
                "share": 0.140,
                "leak_cat": "local_community",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Local Tool & Van Reinvestment",
                "payee_name": "Local Business Capital Account",
                "zip": oz,
                "share": 0.040,
                "leak_cat": "local_community",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
        ]
        insight = (
            f"A private equity rollup operating under a legacy local name drains 38¢ of every dollar to PE management fees and 40¢ to national overhead. "
            f"Hiring an independent owner-operator keeps 100% recirculating in your town."
        )

    else:  # default: grocery_produce
        title = "Grocery: Conventional Supermarket Chain vs. Food Co-op & Community Farm"
        conv_nodes = [
            {
                "role": "Industrial Agribusiness Farm Gate",
                "payee_name": "Corporate-Contracted Monoculture Farm",
                "zip": "72764",
                "share": 0.147,
                "leak_cat": "corporate_overhead",
                "func_cat": "worker_farmer",
                "farm_tier": "contract_grower",
                "farm_notes": "Contracted to agribusiness distributor. Subject to commodity spot pricing; land often leased from farmland REITs.",
            },
            {
                "role": "Frontline Store Workers & Cashiers",
                "payee_name": "Supermarket Hourly Store Staff",
                "zip": oz,
                "share": 0.125,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "CPG Processing, Transport & Packaging",
                "payee_name": "General Mills CPG Manufacturing",
                "zip": "55426",
                "share": 0.283,
                "leak_cat": "corporate_overhead",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Corporate Brand Marketing & Advertising",
                "payee_name": "Madison Avenue Ad Agencies",
                "zip": "10001",
                "share": 0.085,
                "leak_cat": "corporate_overhead",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Supermarket Store Real Estate Triple-Net REIT",
                "payee_name": "Commercial Net Lease REIT (Realty Income Corp)",
                "zip": "92078",
                "share": 0.160,
                "leak_cat": "corporate_overhead",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Corporate Executive Compensation",
                "payee_name": "Supermarket C-Suite & Stock Grants",
                "zip": "72716",
                "share": 0.042,
                "leak_cat": "corporate_overhead",
                "func_cat": "executive_shareholder",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Wall Street Buybacks & Institutional Dividends",
                "payee_name": "BlackRock, Vanguard & State Street",
                "zip": "10005",
                "share": 0.158,
                "leak_cat": "wall_street_leak",
                "func_cat": "executive_shareholder",
                "farm_tier": None,
                "farm_notes": None,
            },
        ]
        alt_nodes = [
            {
                "role": "Independent Community Farm Gate",
                "payee_name": "Tangletown Family Farm & Regional Co-op",
                "zip": "55370" if ostate == "MN" else oz,
                "share": 0.420,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": "community_farmer",
                "farm_notes": "100% Independent community grower. 140-acre regenerative family farm, direct harvest, no agribusiness middlemen.",
            },
            {
                "role": "Living Wage Food Co-op Staff",
                "payee_name": "Wedge Community Co-op Union Staff",
                "zip": "55407" if ostate == "MN" else oz,
                "share": 0.285,
                "leak_cat": "local_community",
                "func_cat": "worker_farmer",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Regional Organic Logistics & Cold Storage",
                "payee_name": "Midwest Organic Food Hub",
                "zip": "55415" if ostate == "MN" else oz,
                "share": 0.180,
                "leak_cat": "local_community",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Member Patronage Dividends (Returned to You)",
                "payee_name": "Member Shopper Rebates (Returned to Consumer)",
                "zip": oz,
                "share": 0.065,
                "leak_cat": "local_community",
                "func_cat": "member_dividends",
                "farm_tier": None,
                "farm_notes": None,
            },
            {
                "role": "Community Food Access & Education Grants",
                "payee_name": "Neighborhood Food Sovereignty Fund",
                "zip": oz,
                "share": 0.050,
                "leak_cat": "local_community",
                "func_cat": "operations",
                "farm_tier": None,
                "farm_notes": None,
            },
        ]
        insight = (
            f"At a conventional supermarket, over $20.00 of every $100 is extracted by Wall Street buybacks and executive comp, "
            f"while only $12.50 stays with local frontline store clerks and $14.70 goes to an agribusiness grower. "
            f"At a food co-op, $70.50 goes directly to local family farmers and living-wage staff, with zero Wall Street leakage."
        )

    return title, scenario_id, conv_nodes, alt_nodes, insight


def compute_branch(
    option_type: str,
    display_title: str,
    node_defs: List[dict],
    origin_info: Dict[str, any],
    spend_amount: float,
    summary_text: str,
) -> GeoFlowBranch:
    """Computes calculated nodes, distances, worker share, operations, and capital flight."""
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
    """Computes a full side-by-side dollar routing trace based on user origin ZIP."""
    origin_info = resolve_zip(origin_zip)
    title, cat, conv_defs, alt_defs, insight = build_scenario_data(
        scenario_id, origin_info, spend_amount
    )

    conv_branch = compute_branch(
        option_type="conventional",
        display_title="Conventional Supply Chain & Corporate Agribusiness",
        node_defs=conv_defs,
        origin_info=origin_info,
        spend_amount=spend_amount,
        summary_text="Capital is immediately siphoned across interstate holding companies, Delaware shell entities, and Wall Street funds.",
    )

    alt_branch = compute_branch(
        option_type="alternative",
        display_title="Independent Community Farm & Local Co-op Alternative",
        node_defs=alt_defs,
        origin_info=origin_info,
        spend_amount=spend_amount,
        summary_text="Over 85% of capital recirculates directly within regional independent growers, living-wage workers, and member dividends.",
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
