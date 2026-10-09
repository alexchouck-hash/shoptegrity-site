"""Housing & Rental Integrity Router.

Provides data on US housing demographics, the 6-tier ownership hierarchy,
the $100 rent dollar cash-flow split, institutional mega-landlord registry,
and actionable housing swaps.
"""

from typing import Dict, Any, List
from fastapi import APIRouter

router = APIRouter(prefix="/v1/housing", tags=["Housing & Rental Integrity"])

# Demographic benchmarks from US Census Bureau & Federal Reserve
DEMOGRAPHIC_DATA: Dict[str, Any] = {
    "homeownership_rate_pct": 65.6,
    "renter_rate_pct": 34.4,
    "total_homeowner_households": "85.5 Million",
    "total_renter_households": "44.8 Million",
    "single_family_rentals_count": "15.2 Million",
    "single_family_rentals_share_of_rentals_pct": 33.9,
    "under_35_renter_rate_pct": 62.1,
    "median_homeowner_net_worth_usd": 396200,
    "median_renter_net_worth_usd": 10400,
    "net_worth_wealth_multiplier": 38.1,
    "data_sources": [
        "US Census Bureau Housing Vacancies and Homeownership (CPS/HVS)",
        "Federal Reserve Survey of Consumer Finances (SCF)",
        "Joint Center for Housing Studies of Harvard University (JCHS)",
    ],
}

# Where every $100 in monthly rent flows
RENT_DOLLAR_SPLITS: Dict[str, Any] = {
    "tier_1_clt": {
        "model": "Community Land Trust / Housing Co-op",
        "tier": 1,
        "score": 98,
        "grade": "A+",
        "local_retention_pct": 100.0,
        "wall_street_leakage_pct": 0.0,
        "description": "100% of revenue stays in the building and local community. Zero speculative extraction.",
        "breakdown": [
            {"category": "Direct Maintenance & Local Trades", "cents": 48.0, "destination": "Local tradespeople & contractors"},
            {"category": "Capital Replacement Reserve Fund", "cents": 28.0, "destination": "Future roof/boiler replacement escrow"},
            {"category": "Municipal Property Taxes & Public Schools", "cents": 16.0, "destination": "Local city infrastructure & schools"},
            {"category": "Cooperative Administration & Governance", "cents": 8.0, "destination": "Democratic member management"},
            {"category": "Wall Street / Shareholder Extraction", "cents": 0.0, "destination": "Zero remote extraction ($0)"},
        ],
    },
    "tier_3_mom_pop": {
        "model": "Independent Local 'Mom-and-Pop' Landlord (1-4 Units)",
        "tier": 3,
        "score": 78,
        "grade": "B+",
        "local_retention_pct": 82.0,
        "wall_street_leakage_pct": 18.0,
        "description": "Owner lives locally. Most spending recirculates into local hardware stores, trades, and municipal taxes.",
        "breakdown": [
            {"category": "Mortgage Principal & Interest", "cents": 45.0, "destination": "Local bank or mortgage servicer"},
            {"category": "Property Maintenance & Repairs", "cents": 22.0, "destination": "Local handymen, plumbers, HVAC"},
            {"category": "Property Taxes & Public Services", "cents": 18.0, "destination": "Local school district & county roads"},
            {"category": "Owner Household Income / Retirement", "cents": 15.0, "destination": "Local neighborhood household income"},
            {"category": "Corporate Wall Street Extraction", "cents": 0.0, "destination": "No remote corporate siphon"},
        ],
    },
    "tier_6_institutional": {
        "model": "Wall Street Private Equity / Public Mega-REIT",
        "tier": 6,
        "score": 16,
        "grade": "F",
        "local_retention_pct": 26.0,
        "wall_street_leakage_pct": 74.0,
        "description": "Centralized extraction machine. Revenue flows to Manhattan/Dallas headquarters, debt service, and algorithmic yield pricing.",
        "breakdown": [
            {"category": "Shareholder Dividends & Stock Buybacks", "cents": 32.0, "destination": "Wall Street hedge funds & institutional investors"},
            {"category": "Leveraged Buyout Debt Service", "cents": 24.0, "destination": "Investment banks & bondholders"},
            {"category": "Algorithmic Pricing (RealPage) & Corp HQ", "cents": 18.0, "destination": "Software fees & corporate executive comp"},
            {"category": "Local Property Taxes", "cents": 14.0, "destination": "Local municipality"},
            {"category": "Actual Local Maintenance & Repairs", "cents": 12.0, "destination": "Subcontracted network (frequently deferred)"},
        ],
    },
}

# The 6-Tier Housing Ownership Ladder
OWNERSHIP_LADDER: List[Dict[str, Any]] = [
    {
        "tier": 1,
        "name": "Community Land Trusts (CLTs) & Housing Co-ops",
        "score": 98,
        "grade": "A+",
        "description": "Land held in perpetuity for community benefit; homes sold at restricted affordable prices or governed cooperatively.",
        "retention_rate_pct": 100.0,
        "wall_street_risk": "Zero",
    },
    {
        "tier": 2,
        "name": "Resident & Family Owner-Occupants",
        "score": 92,
        "grade": "A",
        "description": "Primary homeowner living in the residence. 100% of equity accrues to the resident household.",
        "retention_rate_pct": 95.0,
        "wall_street_risk": "Low (except mortgage origination/servicing)",
    },
    {
        "tier": 3,
        "name": "Independent Local 'Mom-and-Pop' Landlords (1-4 Units)",
        "score": 78,
        "grade": "B+",
        "description": "Individual local owners owning 1 to 4 units. Direct human contact, negotiable lease terms, local capital recycling.",
        "retention_rate_pct": 82.0,
        "wall_street_risk": "Minimal",
    },
    {
        "tier": 4,
        "name": "Regional Property Management & Mid-Scale LLCs",
        "score": 58,
        "grade": "C",
        "description": "Commercial entities managing 10 to 200 units. Standardized fees, online portals, market-rate annual escalations.",
        "retention_rate_pct": 55.0,
        "wall_street_risk": "Moderate",
    },
    {
        "tier": 5,
        "name": "Institutional Single-Family Rental (SFR) Rollups",
        "score": 28,
        "grade": "D-",
        "description": "Private equity platforms bulk-purchasing entry-level starter homes. Concentrated in Sunbelt metros.",
        "retention_rate_pct": 32.0,
        "wall_street_risk": "High (automated evictions, maintenance delays)",
    },
    {
        "tier": 6,
        "name": "Mega Private Equity Firms & Public Apartment REITs",
        "score": 16,
        "grade": "F",
        "description": "Wall Street giants utilizing algorithmic revenue-management software (RealPage) to maximize rents and extract capital.",
        "retention_rate_pct": 26.0,
        "wall_street_risk": "Severe (DOJ antitrust lawsuits for price fixing)",
    },
]

# Major Corporate Landlords & Evidence Records
MEGA_LANDLORDS: List[Dict[str, Any]] = [
    {
        "name": "Invitation Homes",
        "ticker": "NYSE: INVH",
        "cik": "0001687229",
        "ownership_type": "Public REIT (Spun off from Blackstone)",
        "tier": 5,
        "score": 26,
        "grade": "F",
        "portfolio_units": "~85,000 Single-Family Homes",
        "key_markets": "Atlanta, Phoenix, Dallas, Tampa, Charlotte, Southern California",
        "ceo_pay_ratio": "165:1 (SEC Item 402(u))",
        "algorithmic_pricing": "Yes (YieldStar / RealPage User)",
        "regulatory_citations": [
            {"agency": "FTC / CFPB", "detail": "Settled federal inquiry regarding deceptive utility fee markups and withheld security deposits."},
            {"agency": "US House Financial Services Committee", "detail": "Subpoenaed for documented high eviction filing rates during housing moratoriums."},
        ],
        "warning_flag": "Concentrated in entry-level starter home neighborhoods, outbidding first-time homebuyers with all-cash institutional offers.",
    },
    {
        "name": "Progress Residential (Pretium Partners)",
        "ticker": "Private Equity",
        "cik": None,
        "ownership_type": "Private Equity Fund Platform",
        "tier": 5,
        "score": 22,
        "grade": "F",
        "portfolio_units": "~85,000 Single-Family Homes",
        "key_markets": "Atlanta, Phoenix, Charlotte, Nashville, Las Vegas, Orlando",
        "ceo_pay_ratio": "Not Disclosed (Private)",
        "algorithmic_pricing": "Yes",
        "regulatory_citations": [
            {"agency": "Congressional Investigation (2022)", "detail": "Filed evictions at nearly double the rate of independent landlords across Georgia and Florida."},
            {"agency": "State AG Inquiries", "detail": "Subject of tenant class actions regarding automated maintenance portals and unreturned security deposits."},
        ],
        "warning_flag": "Disguised ownership: Homes are rented through dozens of obscure shell LLCs while tenants communicate only through offshore app call centers.",
    },
    {
        "name": "Blackstone Inc. (Tricon Residential)",
        "ticker": "NYSE: BX",
        "cik": "0001393818",
        "ownership_type": "Global Private Equity Asset Manager",
        "tier": 6,
        "score": 18,
        "grade": "F",
        "portfolio_units": "~37,000 SFR Homes + 300,000+ Multi-Family Units Globally",
        "key_markets": "Global (Sunbelt US, Canada, UK, Western Europe)",
        "ceo_pay_ratio": "320:1",
        "algorithmic_pricing": "Yes (Enterprise algorithmic asset management)",
        "regulatory_citations": [
            {"agency": "United Nations Special Rapporteur on Housing", "detail": "Formally cited for financializing global housing markets and exacerbating homelessness."},
            {"agency": "SEC Form 10-K", "detail": "$3.5 Billion acquisition of Tricon Residential completed in 2024 to expand single-family rental footprint."},
        ],
        "warning_flag": "World's largest corporate landlord. Leverages sovereign wealth and pension capital to treat residential shelter as an extraction asset class.",
    },
    {
        "name": "Greystar Real Estate Partners",
        "ticker": "Private Real Estate Conglomerate",
        "cik": None,
        "ownership_type": "Global Property Management & Development Firm",
        "tier": 6,
        "score": 19,
        "grade": "F",
        "portfolio_units": "800,000+ Multi-Family Units Managed Worldwide",
        "key_markets": "National across 50 US metros",
        "ceo_pay_ratio": "Private",
        "algorithmic_pricing": "Yes (Primary RealPage Co-conspirator)",
        "regulatory_citations": [
            {"agency": "US Department of Justice (DOJ)", "detail": "Named in landmark federal antitrust lawsuit (DOJ v. RealPage, 2024) for alleged algorithmic rent price-fixing."},
            {"agency": "DC Attorney General", "detail": "Sued for participating in district-wide rent-setting exchange that inflated apartment prices by up to 15%."},
        ],
        "warning_flag": "Manages hundreds of 'luxury' apartment towers under local-sounding names while sharing non-public tenant lease data with central pricing algorithms.",
    },
    {
        "name": "American Homes 4 Rent (AMH)",
        "ticker": "NYSE: AMH",
        "cik": "0001562401",
        "ownership_type": "Public REIT",
        "tier": 5,
        "score": 25,
        "grade": "F",
        "portfolio_units": "~60,000 Single-Family Homes",
        "key_markets": "Midwest, Southeast, Texas",
        "ceo_pay_ratio": "142:1 (SEC Form DEF 14A)",
        "algorithmic_pricing": "Yes",
        "regulatory_citations": [
            {"agency": "Consumer Financial Protection Bureau (CFPB)", "detail": "Monitored for mandatory fee transparency and automated late penalty charges."},
        ],
        "warning_flag": "Pioneered 'build-to-rent' subdivisions where entire neighborhoods of new homes are built exclusively for permanent rental, blocking homeownership.",
    },
]

# Actionable Housing Swaps
HOUSING_SWAPS: List[Dict[str, Any]] = [
    {
        "title": "Corporate Apartment Complex -> Local Duplex / Independent Multi-Family",
        "category": "Renting",
        "bad_model": "Wall Street managed complex with $150/mo mandatory amenity & trash fees",
        "good_model": "Independent local landlord owning 1-4 units, duplex, or member co-op",
        "financial_impact": "Saves $1,800 - $3,600 per year in eliminated junk fees; human lease negotiation",
        "integrity_gain": "Shifts rent from remote private equity extraction to local community recirculation",
    },
    {
        "title": "Big Wall Street Bank Mortgage -> Community Credit Union Mortgage",
        "category": "Financing",
        "bad_model": "Wells Fargo / Chase mortgage with high origination fees, bundled and sold to Wall Street",
        "good_model": "Member-owned local credit union or mutual savings bank with portfolio servicing",
        "financial_impact": "Saves $3,000 - $8,000 in closing fees; mortgage payments fund local community loans",
        "integrity_gain": "Profits return to credit union members via lower loan rates and higher deposit dividends",
    },
    {
        "title": "Speculative Market Starter Home -> Community Land Trust (CLT) Home",
        "category": "Purchasing",
        "bad_model": "Bidding wars against institutional cash buyers for inflated suburban starter homes",
        "good_model": "Community Land Trust purchase (buying house, leasing land under perpetual trust)",
        "financial_impact": "Purchase price is 25% - 40% below market value; insulated from market crashes",
        "integrity_gain": "Permanent community equity; prevents speculative flipping and preserves neighborhood stability",
    },
    {
        "title": "Single-Family Primary Purchase -> FHA 3.5% 'House Hacking' (2-4 Units)",
        "category": "Wealth Building",
        "bad_model": "Stretching budget to pay 100% of mortgage on a standalone house with 0 rental offset",
        "good_model": "Buying a duplex, triplex, or fourplex with 3.5% down FHA; tenant rent offsets mortgage",
        "financial_impact": "Cuts net housing costs by 60% - 100%; tenants pay down your real estate equity",
        "integrity_gain": "Enables working families to build generational wealth while providing fair, local housing to neighbors",
    },
]


@router.get("/overview")
def get_housing_overview() -> Dict[str, Any]:
    """Returns comprehensive housing and rental integrity data."""
    return {
        "demographics": DEMOGRAPHIC_DATA,
        "rent_dollar_splits": RENT_DOLLAR_SPLITS,
        "ownership_ladder": OWNERSHIP_LADDER,
        "mega_landlords": MEGA_LANDLORDS,
        "swaps": HOUSING_SWAPS,
    }


@router.get("/rent-split")
def get_rent_split() -> Dict[str, Any]:
    """Returns the $100 rent dollar cash-flow breakdown across tiers."""
    return RENT_DOLLAR_SPLITS


@router.get("/landlords")
def get_mega_landlords() -> List[Dict[str, Any]]:
    """Returns the registry of institutional mega-landlords with evidence citations."""
    return MEGA_LANDLORDS
