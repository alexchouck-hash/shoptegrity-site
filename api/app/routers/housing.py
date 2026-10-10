"""Housing & Rental Integrity Router.

Data behind /housing and /v1/housing: a tenure overview, the ownership-model
ladder (with Shoptegrity opinion grades), an illustrative rent-dollar split,
the landlord registry, and housing swap guidance.

Sourcing rule: a figure or factual claim about a named party is kept only with
a cited source. Anything without one is None, an empty list, or the text
"Withheld: no cited source yet". Route paths and key names are kept stable.
"""

from typing import Dict, Any, List
from fastapi import APIRouter

router = APIRouter(prefix="/v1/housing", tags=["Housing & Rental Integrity"])

WITHHELD = "Withheld: no cited source yet"
OPINION_LABEL = "Shoptegrity opinion"
ILLUSTRATIVE_LABEL = "Illustrative input for a calculator. Not a measurement. No cited source yet."

# Every figure is withheld (None) until it is linked to a cited source table.
# data_sources lists candidate sources to cite; no figure is cited to them yet.
DEMOGRAPHIC_DATA: Dict[str, Any] = {
    "status": WITHHELD,
    "homeownership_rate_pct": None,
    "renter_rate_pct": None,
    "total_homeowner_households": None,
    "total_renter_households": None,
    "single_family_rentals_count": None,
    "single_family_rentals_share_of_rentals_pct": None,
    "under_35_renter_rate_pct": None,
    "median_homeowner_net_worth_usd": None,
    "median_renter_net_worth_usd": None,
    "net_worth_wealth_multiplier": None,
    "data_sources": [
        "US Census Bureau Housing Vacancies and Homeownership (CPS/HVS)",
        "Federal Reserve Survey of Consumer Finances (SCF)",
        "Joint Center for Housing Studies of Harvard University (JCHS)",
    ],
}


def _split_tier(model: str, tier: int, description: str, breakdown: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Builds one illustrative split. Local and outside shares are summed from the breakdown."""
    total = round(sum(row["cents"] for row in breakdown), 1)
    if total != 100.0:
        raise ValueError(f"Illustrative split for {model!r} sums to {total}, not 100")
    outside = round(sum(row["cents"] for row in breakdown if row["outside"]), 1)
    return {
        "model": model,
        "tier": tier,
        "label": ILLUSTRATIVE_LABEL,
        "local_retention_pct": round(100.0 - outside, 1),
        "wall_street_leakage_pct": outside,
        "description": description,
        "breakdown": breakdown,
    }


# Where every $100 of rent could go, as an illustrative example only.
# The cents are example inputs, not measurements of any landlord or company.
RENT_DOLLAR_SPLITS: Dict[str, Any] = {
    "tier_1_clt": _split_tier(
        model="Community Land Trust / Housing Co-op (example)",
        tier=1,
        description="Example allocation for illustration only. Not a measurement.",
        breakdown=[
            {"category": "Direct maintenance & local trades", "cents": 48.0, "destination": "Local tradespeople & contractors", "outside": False},
            {"category": "Capital replacement reserve", "cents": 28.0, "destination": "Reserve fund for future replacements", "outside": False},
            {"category": "Municipal property taxes & schools", "cents": 16.0, "destination": "Local government and schools", "outside": False},
            {"category": "Cooperative administration & governance", "cents": 8.0, "destination": "Member governance", "outside": False},
            {"category": "Outside shareholder distributions", "cents": 0.0, "destination": "None assumed in this example", "outside": True},
        ],
    ),
    "tier_3_mom_pop": _split_tier(
        model="Independent Local Owner, 1-4 Units (example)",
        tier=3,
        description="Example allocation for illustration only. The interest line assumes an out-of-area lender.",
        breakdown=[
            {"category": "Mortgage principal", "cents": 27.0, "destination": "Local lender", "outside": False},
            {"category": "Mortgage interest", "cents": 18.0, "destination": "Out-of-area lender (example assumption)", "outside": True},
            {"category": "Property maintenance & repairs", "cents": 22.0, "destination": "Local handymen, plumbers, HVAC", "outside": False},
            {"category": "Property taxes & public services", "cents": 18.0, "destination": "Local school district & county", "outside": False},
            {"category": "Owner household income / retirement", "cents": 15.0, "destination": "Owner's household", "outside": False},
        ],
    ),
    "tier_6_institutional": _split_tier(
        model="Large Investor Owner (example)",
        tier=6,
        description="Example allocation for illustration only. Not a measurement.",
        breakdown=[
            {"category": "Shareholder distributions & buybacks", "cents": 32.0, "destination": "Investors and shareholders", "outside": True},
            {"category": "Acquisition loan debt service", "cents": 24.0, "destination": "Lenders and bondholders", "outside": True},
            {"category": "Software fees & corporate overhead", "cents": 18.0, "destination": "Software vendors and corporate offices", "outside": True},
            {"category": "Local property taxes", "cents": 14.0, "destination": "Local municipality", "outside": False},
            {"category": "Local maintenance & repairs", "cents": 12.0, "destination": "Contracted local network", "outside": False},
        ],
    ),
}

# The 6-tier ownership ladder. Grades use the same bands as the brand pages:
# A 90-100, B 70-89, C 50-69, D 30-49, F under 30.
OWNERSHIP_LADDER: List[Dict[str, Any]] = [
    {
        "tier": 1,
        "name": "Community Land Trusts (CLTs) & Housing Co-ops",
        "score": 98,
        "grade": "A",
        "rating_label": OPINION_LABEL,
        "description": "Land is held in trust for community benefit; homes are sold at restricted prices or governed cooperatively.",
    },
    {
        "tier": 2,
        "name": "Resident & Family Owner-Occupants",
        "score": 92,
        "grade": "A",
        "rating_label": OPINION_LABEL,
        "description": "Primary homeowner living in the residence. Mortgage principal payments build equity over time; the amount depends on loan terms.",
    },
    {
        "tier": 3,
        "name": "Independent Local 'Mom-and-Pop' Landlords (1-4 Units)",
        "score": 78,
        "grade": "B",
        "rating_label": OPINION_LABEL,
        "description": "Individual owners who rent out 1 to 4 units. Direct contact and negotiable lease terms are possible.",
    },
    {
        "tier": 4,
        "name": "Regional Property Management & Mid-Scale LLCs",
        "score": 58,
        "grade": "C",
        "rating_label": OPINION_LABEL,
        "description": "Commercial entities managing about 10 to 200 units. Standardized leases and online portals are typical.",
    },
    {
        "tier": 5,
        "name": "Institutional Single-Family Rental (SFR) Rollups",
        "score": 28,
        "grade": "F",
        "rating_label": OPINION_LABEL,
        "description": "Institutional investors that buy starter family homes, sometimes in bulk.",
    },
    {
        "tier": 6,
        "name": "Large Private Equity Firms & Public Apartment REITs",
        "score": 16,
        "grade": "F",
        "rating_label": OPINION_LABEL,
        "description": "Large private equity funds and publicly traded apartment REITs.",
    },
]

# Landlord registry. No records are published yet: Withheld: no cited source yet.
MEGA_LANDLORDS: List[Dict[str, Any]] = []

# Housing swaps. Non-numeric guidance only; savings and price figures are withheld.
HOUSING_SWAPS: List[Dict[str, Any]] = [
    {
        "title": "Corporate Complex -> Local Duplex / Co-op",
        "category": "Renting",
        "bad_model": "Large apartment complex with mandatory amenity, trash and portal fees added to rent",
        "good_model": "Independent local landlord with 1-4 units, a duplex, or a housing co-op",
        "financial_impact": "Add up every mandatory fee in your lease and compare the total with the alternative. Savings amounts: Withheld: no cited source yet",
        "integrity_gain": "Rent may stay in the local community. Check each owner's structure and governing documents",
    },
    {
        "title": "Large National Bank -> Community Credit Union",
        "category": "Financing",
        "bad_model": "Taking the first mortgage offer without comparing fees and rates",
        "good_model": "Member-owned local credit union. Ask whether it keeps and services the loans it makes",
        "financial_impact": "Compare the Loan Estimate fees and rate from each lender. Closing-cost amounts: Withheld: no cited source yet",
        "integrity_gain": "Credit unions are member-owned; compare their terms directly with other lenders",
    },
    {
        "title": "Competitive Market Home -> Community Land Trust",
        "category": "Purchasing",
        "bad_model": "Bidding against cash buyers in a competitive market",
        "good_model": "Community land trust purchase: you buy the home and lease the land from the trust",
        "financial_impact": "Purchase price and resale rules come from the trust's ground lease. Price discounts: Withheld: no cited source yet. Read the resale terms first",
        "integrity_gain": "Land stays in trust, which can limit speculative resale; check the lease terms for the specific trust",
    },
    {
        "title": "Standalone House -> Multi-Unit 'House Hacking'",
        "category": "Wealth Building",
        "bad_model": "Paying the full mortgage from your own income with no rental income",
        "good_model": "Buy a 2-4 unit property, live in one unit and rent the others, if loan rules allow it",
        "financial_impact": "Rent from other units can offset part of the housing cost. Amounts depend on local rents and loan rules: Withheld: no cited source yet",
        "integrity_gain": "Owner-occupants can house neighbors in the other units; check local rules for rental registration",
    },
]


@router.get("/overview")
def get_housing_overview() -> Dict[str, Any]:
    """Returns housing and rental data, with withheld figures set to None."""
    return {
        "demographics": DEMOGRAPHIC_DATA,
        "rent_dollar_splits": RENT_DOLLAR_SPLITS,
        "ownership_ladder": OWNERSHIP_LADDER,
        "mega_landlords": MEGA_LANDLORDS,
        "swaps": HOUSING_SWAPS,
    }


@router.get("/rent-split")
def get_rent_split() -> Dict[str, Any]:
    """Returns the illustrative $100 rent split across example owner models."""
    return RENT_DOLLAR_SPLITS


@router.get("/landlords")
def get_mega_landlords() -> List[Dict[str, Any]]:
    """Returns the landlord registry. Empty until records have cited sources."""
    return MEGA_LANDLORDS
