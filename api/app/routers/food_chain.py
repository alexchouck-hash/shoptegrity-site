from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.app.db.session import get_db, haversine_distance_km
from api.app.models.core import Maker, Place, SpendCategory
from api.app.schemas.domain import (
    MakerSummary,
    PlaceSummary,
    FoodDollarSplit,
    FarmlandOwnershipStats,
)

router = APIRouter(prefix="/v1/food", tags=["Food Chain Integrity"])

# Shown in place of any figure, citation or claim that has no cited source (name + URL) in the repo.
WITHHELD = "Withheld: no cited source yet"
# Shown in place of a maker or place name that has no cited source.
LISTED_NOT_VERIFIED = "Listed, not verified"


# Response models whose figure fields are Optional, so a withheld value serializes as null.
# They subclass the shared schemas in api/app/schemas/domain.py, which still require values.

class FoodDollarSplitPublic(FoodDollarSplit):
    farm_share_cents: Optional[float] = None
    food_processing_cents: Optional[float] = None
    packaging_cents: Optional[float] = None
    transportation_cents: Optional[float] = None
    wholesale_trade_cents: Optional[float] = None
    retail_trade_cents: Optional[float] = None
    food_services_cents: Optional[float] = None
    energy_cents: Optional[float] = None
    finance_insurance_cents: Optional[float] = None
    advertising_cents: Optional[float] = None
    other_cents: Optional[float] = None
    year: Optional[int] = None


class FarmlandOwnershipStatsPublic(FarmlandOwnershipStats):
    total_us_farmland_acres: Optional[str] = None
    rented_percentage: Optional[float] = None
    rented_acres: Optional[str] = None
    non_operator_landlord_pct: Optional[float] = None
    non_operators_never_farmed_pct: Optional[float] = None
    corn_belt_rented_pct_range: Optional[str] = None
    owner_operator_pct: Optional[float] = None
    institutional_investor_pct: Optional[float] = None
    foreign_investor_pct: Optional[float] = None
    top_100_landowners_pct: Optional[float] = None


class PlaceSummaryPublic(PlaceSummary):
    slug: Optional[str] = None
    ownership_tier: Optional[int] = None
    verified_locally: Optional[bool] = None


class MakerSummaryPublic(MakerSummary):
    makes_own: Optional[bool] = None
    place: Optional[PlaceSummaryPublic] = None


# Shoptegrity framework (opinion). The tier names and descriptions are judgments, not measurements.
# producer_dollar_share_pct is withheld for every tier: no cited source yet.
SOURCING_LADDER = [
    {
        "tier": 1,
        "name": "Own Garden / Home Grown",
        "description": "Grown and eaten at home. No outside supply chain, and the household controls growing and handling.",
        "producer_dollar_share_pct": None,
        "recommendation": "Top tier in this framework. Grow kitchen herbs, greens, tomatoes if space allows.",
    },
    {
        "tier": 2,
        "name": "Community Garden / Gleaning / Barter",
        "description": "Retained locally, builds commons, strengthens neighborhood food sovereignty.",
        "producer_dollar_share_pct": None,
        "recommendation": "Join or support local urban community plots and food-sharing networks.",
    },
    {
        "tier": 3,
        "name": "Direct from Local Farm or Maker (CSA, Farm Stand, U-Pick)",
        "description": "Buys direct from a local producer. The framework judges that most of the price reaches the producer; no share figure is published.",
        "producer_dollar_share_pct": None,
        "recommendation": "Subscribe to a local CSA box or visit weekly farm stands.",
    },
    {
        "tier": 4,
        "name": "Local Food Co-op Selling Local Goods",
        "description": "Local producer is paid wholesale. Co-op margin can return to member-owners as patronage dividends.",
        "producer_dollar_share_pct": None,
        "recommendation": "Shop member-owned natural food cooperatives for regional staples.",
    },
    {
        "tier": 5,
        "name": "Direct from Non-Local Producer (Mail Order)",
        "description": "Framework judgment: most of the purchase price reaches the producer, but the purchase carries a transport and packaging footprint.",
        "producer_dollar_share_pct": None,
        "recommendation": "Great for single-origin tea, specialty grains, or artisan olive oils not grown in your region.",
    },
    {
        "tier": 6,
        "name": "Large Regional Chain Selling Local Goods",
        "description": "Local grower gets shelf space and payment, but grocery chain margin leaves the immediate community.",
        "producer_dollar_share_pct": None,
        "recommendation": "Look for regional farm tags on conventional supermarket shelves.",
    },
    {
        "tier": 7,
        "name": "Local Co-op Selling National Goods",
        "description": "Retail margin stays local and democratic, but the supply chain is long and multinational.",
        "producer_dollar_share_pct": None,
        "recommendation": "Acceptable for bananas, citrus, coffee where local cultivation is impossible.",
    },
    {
        "tier": 8,
        "name": "National Supermarket Chain, Non-Local Whole Goods",
        "description": "Long global supply chain and corporate retail margin. Framework judgment; no share figure is published.",
        "producer_dollar_share_pct": None,
        "recommendation": "Transition items up the ladder to Tier 3 or 4 when budget permits.",
    },
    {
        "tier": 9,
        "name": "National Chain, Ultra-Processed, Conglomerate Brand",
        "description": "Longest supply chain, with the most packaging, advertising, and corporate overhead steps in the framework. Framework judgment; no share figure is published.",
        "producer_dollar_share_pct": None,
        "recommendation": "Swap for whole ingredients and co-op brands where you can.",
    },
]


@router.get("/sourcing-ladder")
def get_sourcing_ladder():
    """Shoptegrity framework (opinion): 9-tier food sourcing ladder. Producer dollar share figures are withheld: no cited source yet."""
    return {
        "title": "The Universal Food Sourcing Ladder (Shoptegrity opinion)",
        "description": (
            "Shoptegrity framework (opinion) that orders purchase channels from tier 1 (grown at home) to tier 9. "
            "The order is a framework judgment about how directly a purchase reaches the grower or maker and how much "
            "value stays local. It is not computed from producer dollar shares, which are withheld: no cited source yet. "
            "Where local retention and directness point different ways (for example tier 4 and tier 5), the tier number "
            "reflects the framework's judgment."
        ),
        "tiers": SOURCING_LADDER,
    }


@router.get("/makers", response_model=List[MakerSummaryPublic])
def get_food_makers(
    product: Optional[str] = Query(None, description="Filter by product (e.g. Tea, Honey, Apples)"),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    radius_km: float = Query(50.0),
    organic_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Listed, not verified. Maker names, makes-own status, certifications and verification are withheld: no cited source yet."""
    if organic_only:
        # Certifications are withheld (no cited source yet), so no entry can be matched on them.
        return []

    query = db.query(Maker)
    makers = query.all()

    results = []
    for m in makers:
        if product:
            prod_match = any(product.lower() in p.lower() for p in (m.products or []))
            if not prod_match:
                continue

        place_summary = None
        if m.place:
            dist = None
            if lat is not None and lon is not None:
                dist = haversine_distance_km(lat, lon, m.place.lat, m.place.lon)
                if dist > radius_km:
                    continue

            place_summary = PlaceSummaryPublic(
                id=m.place.id,
                name=LISTED_NOT_VERIFIED,
                slug=None,
                category=m.place.category,
                address=m.place.address,
                city=m.place.city,
                state=m.place.state,
                postal_code=m.place.postal_code,
                lat=m.place.lat,
                lon=m.place.lon,
                phone=m.place.phone,
                website=m.place.website,
                ownership_tier=None,
                flags=[],
                verified_locally=None,
                verified_how=WITHHELD,
                hours=m.place.hours,
                season=m.place.season,
                distance_km=dist,
            )

        results.append(
            MakerSummaryPublic(
                id=m.id,
                name=LISTED_NOT_VERIFIED,
                products=m.products or [],
                makes_own=None,
                makes_own_evidence=WITHHELD,
                certifications=[],
                sourcing_ladder_tier=m.sourcing_ladder_tier,
                where_to_buy=m.where_to_buy,
                direct_order_url=m.direct_order_url,
                place=place_summary,
            )
        )

    # Sort by distance if location provided
    if lat is not None and lon is not None:
        results.sort(key=lambda x: (x.place.distance_km if x.place and x.place.distance_km is not None else 999999))

    return results


def fetch_food_dollar_splits(category: Optional[str] = None) -> List[FoodDollarSplitPublic]:
    """Food dollar split by product category. Every figure, year and citation is withheld: no cited source yet."""
    # All figure fields default to None in FoodDollarSplitPublic, so only the labels and withheld text are set here.
    splits = [
        FoodDollarSplitPublic(
            product_category="Overall U.S. Food Average",
            source_citation=WITHHELD,
            summary_insight=WITHHELD,
        ),
        FoodDollarSplitPublic(
            product_category="Fresh Fruits & Vegetables",
            source_citation=WITHHELD,
            summary_insight=WITHHELD,
        ),
        FoodDollarSplitPublic(
            product_category="Dairy & Fluid Milk",
            source_citation=WITHHELD,
            summary_insight=WITHHELD,
        ),
        FoodDollarSplitPublic(
            product_category="Processed Grains & Packaged Foods",
            source_citation=WITHHELD,
            summary_insight=WITHHELD,
        ),
    ]

    if category and isinstance(category, str):
        splits = [s for s in splits if category.lower() in s.product_category.lower()]
    return splits


@router.get("/dollar-split", response_model=List[FoodDollarSplitPublic])
def get_food_dollar_split(category: Optional[str] = Query(None)):
    return fetch_food_dollar_splits(category)


# Every statistic below lacks a cited source (name + URL) in the repo, so each is withheld (None).
# Named landowner profiles and their rank, acreage and water notes are removed until each has a cited source.
FARMLAND_OWNERSHIP_DATA = FarmlandOwnershipStatsPublic(
    total_us_farmland_acres=None,
    rented_percentage=None,
    rented_acres=None,
    non_operator_landlord_pct=None,
    non_operators_never_farmed_pct=None,
    corn_belt_rented_pct_range=None,
    owner_operator_pct=None,
    institutional_investor_pct=None,
    foreign_investor_pct=None,
    top_100_landowners_pct=None,
    top_elite_landowners=[],
    sources=[],
)


# Enterprise cost categories are kept as labels. Amounts, shares, beneficiaries and take-home figures
# are withheld (None or WITHHELD) because none has a cited source (name + URL) in the repo.
FARM_BUDGET_COMPARISONS = [
    {
        "id": "commodity_corn_soy",
        "title": "Conventional Commodity Grain (Corn / Soybeans)",
        "sector": "Row Crops & Industrial Grain",
        "gross_farm_gate": None,
        "retail_context": WITHHELD,
        "expenses": [
            {
                "name": "Cash Rent & Land Mortgage",
                "amount": None,
                "pct": None,
                "beneficiaries": WITHHELD,
                "color": "#94a3b8",
            },
            {
                "name": "Synthetic Fertilizer (NPK)",
                "amount": None,
                "pct": None,
                "beneficiaries": WITHHELD,
                "color": "#f59e0b",
            },
            {
                "name": "Machinery Depreciation, Tech & Fuel",
                "amount": None,
                "pct": None,
                "beneficiaries": WITHHELD,
                "color": "#64748b",
            },
            {
                "name": "Patented GMO Seed",
                "amount": None,
                "pct": None,
                "beneficiaries": WITHHELD,
                "color": "#dc2626",
            },
            {
                "name": "Crop Protection (Herbicides/Pesticides)",
                "amount": None,
                "pct": None,
                "beneficiaries": WITHHELD,
                "color": "#ea580c",
            },
            {
                "name": "Operating Loan Interest & Insurance",
                "amount": None,
                "pct": None,
                "beneficiaries": WITHHELD,
                "color": "#6b7280",
            },
        ],
        "net_farmer_income": None,
        "net_farmer_pct": None,
        "take_home_notes": WITHHELD,
    },
    {
        "id": "contract_poultry_cafo",
        "title": "Contract Poultry Grower (CAFO Broilers)",
        "sector": "Livestock & Poultry Integration",
        "gross_farm_gate": None,
        "retail_context": WITHHELD,
        "expenses": [
            {
                "name": "Mortgage Debt on Barns",
                "amount": None,
                "pct": None,
                "beneficiaries": WITHHELD,
                "color": "#94a3b8",
            },
            {
                "name": "Propane Heat & Electricity (Tunnel Fans)",
                "amount": None,
                "pct": None,
                "beneficiaries": WITHHELD,
                "color": "#f59e0b",
            },
            {
                "name": "Barn Maintenance, Litter & Repairs",
                "amount": None,
                "pct": None,
                "beneficiaries": WITHHELD,
                "color": "#64748b",
            },
        ],
        "net_farmer_income": None,
        "net_farmer_pct": None,
        "take_home_notes": WITHHELD,
    },
    {
        "id": "independent_community_farm",
        "title": "Independent Family Farm & Food Co-op (Direct Sales)",
        "sector": "Direct-to-Consumer & Cooperative",
        "gross_farm_gate": None,
        "retail_context": WITHHELD,
        "expenses": [
            {
                "name": "Equipment Care & Solar/Renewable Fuel",
                "amount": None,
                "pct": None,
                "beneficiaries": WITHHELD,
                "color": "#34d399",
            },
            {
                "name": "Land Equity & Watershed Reserve",
                "amount": None,
                "pct": None,
                "beneficiaries": WITHHELD,
                "color": "#0d9488",
            },
            {
                "name": "Soil Health, Cover Crops & Organic Seed",
                "amount": None,
                "pct": None,
                "beneficiaries": WITHHELD,
                "color": "#059669",
            },
            {
                "name": "Patented GMO Seed & Chemical Bills",
                "amount": None,
                "pct": None,
                "beneficiaries": WITHHELD,
                "color": "#cbd5e1",
            },
        ],
        "net_farmer_income": None,
        "net_farmer_pct": None,
        "take_home_notes": WITHHELD,
    },
]


@router.get("/farmland-ownership", response_model=FarmlandOwnershipStatsPublic)
def get_farmland_ownership():
    """Farmland tenure and ownership statistics. Every figure and source is withheld: no cited source yet."""
    return FARMLAND_OWNERSHIP_DATA


@router.get("/farm-budgets")
def get_farm_budgets():
    """Shoptegrity framework of enterprise cost categories. Amounts, shares and take-home figures are withheld: no cited source yet."""
    return {
        "title": "Farm-Gate Cost Decomposition (figures withheld: no cited source yet)",
        "description": "Cost categories for three enterprise types, as a Shoptegrity framework (opinion). Amounts and shares are withheld: no cited source yet.",
        "comparisons": FARM_BUDGET_COMPARISONS,
    }
