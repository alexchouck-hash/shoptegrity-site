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
    EliteLandownerProfile,
    FarmGateAudit,
    FarmGateCostItem,
)

router = APIRouter(prefix="/v1/food", tags=["Food Chain Integrity"])

# Sourcing Ladder constant from market analysis
SOURCING_LADDER = [
    {
        "tier": 1,
        "name": "Own Garden / Home Grown",
        "description": "~100% of value retained, zero transport, absolute freshness and control.",
        "producer_dollar_share_pct": 100.0,
        "recommendation": "Highest integrity tier. Grow kitchen herbs, greens, tomatoes if space allows.",
    },
    {
        "tier": 2,
        "name": "Community Garden / Gleaning / Barter",
        "description": "Retained locally, builds commons, strengthens neighborhood food sovereignty.",
        "producer_dollar_share_pct": 95.0,
        "recommendation": "Join or support local urban community plots and food-sharing networks.",
    },
    {
        "tier": 3,
        "name": "Direct from Local Farm or Maker (CSA, Farm Stand, U-Pick)",
        "description": "Producer captures 85-95% of the dollar. Directly enriches local family growers and regenerators.",
        "producer_dollar_share_pct": 90.0,
        "recommendation": "Subscribe to a local CSA box or visit weekly farm stands.",
    },
    {
        "tier": 4,
        "name": "Local Food Co-op Selling Local Goods",
        "description": "Local producer paid fair wholesale; operational margin recirculates to member-owners as patronage dividends.",
        "producer_dollar_share_pct": 65.0,
        "recommendation": "Shop member-owned natural food cooperatives for regional staples.",
    },
    {
        "tier": 5,
        "name": "Direct from Non-Local Producer (Mail Order)",
        "description": "Producer captures most of the purchase price, but carries a transport and packaging footprint.",
        "producer_dollar_share_pct": 75.0,
        "recommendation": "Great for single-origin tea, specialty grains, or artisan olive oils not grown in your region.",
    },
    {
        "tier": 6,
        "name": "Large Regional Chain Selling Local Goods",
        "description": "Local grower gets shelf space and payment, but grocery chain margin leaves the immediate community.",
        "producer_dollar_share_pct": 40.0,
        "recommendation": "Look for regional farm tags on conventional supermarket shelves.",
    },
    {
        "tier": 7,
        "name": "Local Co-op Selling National Goods",
        "description": "Retail margin stays local and democratic, but the supply chain is long and multinational.",
        "producer_dollar_share_pct": 25.0,
        "recommendation": "Acceptable for bananas, citrus, coffee where local cultivation is impossible.",
    },
    {
        "tier": 8,
        "name": "National Supermarket Chain, Non-Local Whole Goods",
        "description": "Long global supply chain, extractive corporate margin, low farm share (under 15¢/dollar).",
        "producer_dollar_share_pct": 14.7,
        "recommendation": "Transition items up the ladder to Tier 3 or 4 when budget permits.",
    },
    {
        "tier": 9,
        "name": "National Chain, Ultra-Processed, Conglomerate Brand",
        "description": "Longest chain, lowest producer share (<8¢), highest corporate ad/packaging/executive comp load.",
        "producer_dollar_share_pct": 7.5,
        "recommendation": "Primary leak in the food dollar. Swap for whole ingredients and co-op brands.",
    },
]


@router.get("/sourcing-ladder")
def get_sourcing_ladder():
    """Returns the 9-tier food sourcing ladder with producer dollar retention estimates."""
    return {
        "title": "The Universal Food Sourcing Ladder",
        "description": "Ranks food procurement channels by how much economic value enriches growers versus extractive intermediaries.",
        "tiers": SOURCING_LADDER,
    }


@router.get("/makers", response_model=List[MakerSummary])
def get_food_makers(
    product: Optional[str] = Query(None, description="Filter by product (e.g. Tea, Honey, Apples)"),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    radius_km: float = Query(50.0),
    organic_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    query = db.query(Maker)
    makers = query.all()

    results = []
    for m in makers:
        if product:
            prod_match = any(product.lower() in p.lower() for p in m.products)
            if not prod_match and product.lower() not in m.name.lower():
                continue

        if organic_only and "USDA Organic" not in m.certifications:
            continue

        place_summary = None
        if m.place:
            dist = None
            if lat is not None and lon is not None:
                dist = haversine_distance_km(lat, lon, m.place.lat, m.place.lon)
                if dist > radius_km:
                    continue

            place_summary = PlaceSummary(
                id=m.place.id,
                name=m.place.name,
                slug=m.place.slug,
                category=m.place.category,
                address=m.place.address,
                city=m.place.city,
                state=m.place.state,
                postal_code=m.place.postal_code,
                lat=m.place.lat,
                lon=m.place.lon,
                phone=m.place.phone,
                website=m.place.website,
                ownership_tier=m.place.ownership_tier,
                flags=m.place.flags or [],
                verified_locally=m.place.verified_locally,
                verified_how=m.place.verified_how,
                hours=m.place.hours,
                season=m.place.season,
                distance_km=dist,
            )

        results.append(
            MakerSummary(
                id=m.id,
                name=m.name,
                products=m.products or [],
                makes_own=m.makes_own,
                makes_own_evidence=m.makes_own_evidence,
                certifications=m.certifications or [],
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


def fetch_food_dollar_splits(category: Optional[str] = None) -> List[FoodDollarSplit]:
    """Returns USDA Economic Research Service (ERS) Food Dollar Series breakdowns."""
    splits = [
        FoodDollarSplit(
            product_category="Overall U.S. Food Average",
            farm_share_cents=11.8,
            food_processing_cents=14.9,
            packaging_cents=2.8,
            transportation_cents=3.4,
            wholesale_trade_cents=10.6,
            retail_trade_cents=14.7,
            food_services_cents=33.2,
            energy_cents=3.6,
            finance_insurance_cents=3.3,
            advertising_cents=2.6,
            other_cents=2.1,
            year=2024,
            source_citation="USDA ERS Food Dollar Series (2024 Release)",
            summary_insight="Farmers and farmworkers receive under 12 cents of every food dollar; marketing and corporate retail capture over 30 cents.",
        ),
        FoodDollarSplit(
            product_category="Fresh Fruits & Vegetables",
            farm_share_cents=18.4,
            food_processing_cents=4.2,
            packaging_cents=6.1,
            transportation_cents=7.8,
            wholesale_trade_cents=15.2,
            retail_trade_cents=34.3,
            food_services_cents=0.0,
            energy_cents=4.1,
            finance_insurance_cents=3.5,
            advertising_cents=3.1,
            other_cents=3.3,
            year=2024,
            source_citation="USDA ERS Food Dollar Series - Fresh Produce Account",
            summary_insight="Buying direct from a CSA or farm stand jumps farm revenue from 18¢ to ~90¢ per dollar.",
        ),
        FoodDollarSplit(
            product_category="Dairy & Fluid Milk",
            farm_share_cents=24.5,
            food_processing_cents=21.0,
            packaging_cents=5.2,
            transportation_cents=4.8,
            wholesale_trade_cents=9.5,
            retail_trade_cents=22.0,
            food_services_cents=0.0,
            energy_cents=4.5,
            finance_insurance_cents=3.2,
            advertising_cents=2.8,
            other_cents=2.5,
            year=2024,
            source_citation="USDA ERS Food Dollar Series - Dairy Account",
            summary_insight="Farmer-owned dairy co-ops return corporate retail margins back to multi-generational dairy families.",
        ),
        FoodDollarSplit(
            product_category="Processed Grains & Packaged Foods",
            farm_share_cents=6.8,
            food_processing_cents=28.5,
            packaging_cents=8.4,
            transportation_cents=5.1,
            wholesale_trade_cents=12.0,
            retail_trade_cents=21.4,
            food_services_cents=0.0,
            energy_cents=4.8,
            finance_insurance_cents=4.0,
            advertising_cents=6.2,
            other_cents=2.8,
            year=2024,
            source_citation="USDA ERS Food Dollar Series - Cereal and Bakery Account",
            summary_insight="For boxed cereals and crackers, advertising and packaging alone cost more than double the actual grain grown by the farmer.",
        ),
    ]

    if category and isinstance(category, str):
        splits = [s for s in splits if category.lower() in s.product_category.lower()]
    return splits


@router.get("/dollar-split", response_model=List[FoodDollarSplit])
def get_food_dollar_split(category: Optional[str] = Query(None)):
    return fetch_food_dollar_splits(category)


FARMLAND_OWNERSHIP_DATA = FarmlandOwnershipStats(
    total_us_farmland_acres="893,400,000",
    rented_percentage=39.2,
    rented_acres="348,000,000",
    non_operator_landlord_pct=80.0,
    non_operators_never_farmed_pct=52.3,
    corn_belt_rented_pct_range="53% – 65%",
    owner_operator_pct=60.8,
    institutional_investor_pct=2.2,
    foreign_investor_pct=3.4,
    top_100_landowners_pct=1.6,
    top_elite_landowners=[
        EliteLandownerProfile(
            name="Stan Kroenke",
            rank=1,
            acreage=2700000,
            acreage_display="2,700,000 acres",
            primary_holdings="Waggoner Ranch (TX), Singleton Ranches (NM), Wyoming & Montana cattle ranges.",
            water_and_resource_notes="Massive private water rights and mineral rights across the American Southwest.",
        ),
        EliteLandownerProfile(
            name="Emmerson Family (Sierra Pacific)",
            rank=2,
            acreage=2440000,
            acreage_display="2,440,000 acres",
            primary_holdings="California, Oregon & Washington timberlands and agricultural valleys.",
            water_and_resource_notes="Nation's second-largest private landholding, controlling headwater mountain watersheds.",
        ),
        EliteLandownerProfile(
            name="John Malone",
            rank=3,
            acreage=2200000,
            acreage_display="2,200,000 acres",
            primary_holdings="Wyoming, Colorado, New Mexico and Maine ranchland and forestry.",
            water_and_resource_notes="Vast western conservation easements, cattle operations, and contiguous habitat blocks.",
        ),
        EliteLandownerProfile(
            name="Ted Turner",
            rank=4,
            acreage=2000000,
            acreage_display="2,000,000 acres",
            primary_holdings="Great Plains and Rocky Mountain bison ranches across NE, MT, NM, SD.",
            water_and_resource_notes="World's largest private bison herd (over 45,000 head); extensive riparian river corridors.",
        ),
        EliteLandownerProfile(
            name="Jeff Bezos",
            rank=24,
            acreage=420000,
            acreage_display="420,000 acres",
            primary_holdings="Corn Ranch (Culberson & Hudspeth Counties, West Texas).",
            water_and_resource_notes="Vast high-desert acreage surrounding aerospace testing with underground aquifer access.",
        ),
        EliteLandownerProfile(
            name="Bill Gates (Cascade Investment)",
            rank=44,
            acreage=275000,
            acreage_display="275,000 acres",
            primary_holdings="Pure high-yield cropland across 18 states (WA, LA, AR, NE, AZ, IL).",
            water_and_resource_notes="Nation's largest private owner of pure farmland; heavy concentration in senior irrigated Columbia Basin and Mississippi Delta soils.",
        ),
        EliteLandownerProfile(
            name="Stewart & Lynda Resnick (The Wonderful Co.)",
            rank=58,
            acreage=190000,
            acreage_display="190,000 acres",
            primary_holdings="California Central Valley (Kern & Fresno Counties) almonds, pistachios, pomegranates.",
            water_and_resource_notes="Controls majority stake in the Kern Water Bank; commands more annual water usage than the entire city of Los Angeles.",
        ),
    ],
    sources=[
        "USDA NASS 2022/2024 Census of Agriculture",
        "USDA ERS Tenure, Ownership, and Transition of Agricultural Land (TOTAL) Survey",
        "The Land Report 100 (2025/2026 Edition)",
        "American Farmland Trust: Farms Under Threat",
    ],
)


FARM_BUDGET_COMPARISONS = [
    {
        "id": "commodity_corn_soy",
        "title": "Conventional Commodity Grain (Corn / Soybeans)",
        "sector": "Row Crops & Industrial Grain",
        "gross_farm_gate": 100.0,
        "retail_context": "Out of $100 spent on cereal or meat at retail, only $14.70 reaches this farm gate, and the farmer nets ~$1.01.",
        "expenses": [
            {
                "name": "Cash Rent & Land Mortgage",
                "amount": 28.00,
                "pct": 28.0,
                "beneficiaries": "Non-Operator Landlords, Farmland REITs, Farm Credit",
                "color": "#94a3b8",
            },
            {
                "name": "Synthetic Fertilizer (NPK)",
                "amount": 21.00,
                "pct": 21.0,
                "beneficiaries": "Nutrien, CF Industries, Mosaic",
                "color": "#f59e0b",
            },
            {
                "name": "Machinery Depreciation, Tech & Fuel",
                "amount": 18.00,
                "pct": 18.0,
                "beneficiaries": "Deere & Co., CNH Industrial, Diesel Refiners",
                "color": "#64748b",
            },
            {
                "name": "Patented GMO Seed",
                "amount": 12.50,
                "pct": 12.5,
                "beneficiaries": "Bayer (Monsanto), Corteva Agriscience",
                "color": "#dc2626",
            },
            {
                "name": "Crop Protection (Herbicides/Pesticides)",
                "amount": 8.50,
                "pct": 8.5,
                "beneficiaries": "Bayer, BASF, Syngenta",
                "color": "#ea580c",
            },
            {
                "name": "Operating Loan Interest & Insurance",
                "amount": 5.00,
                "pct": 5.0,
                "beneficiaries": "Commercial Ag Lenders, Federal Crop Insurance",
                "color": "#6b7280",
            },
        ],
        "net_farmer_income": 7.00,
        "net_farmer_pct": 7.0,
        "take_home_notes": "In down-market commodity years (such as 2024–2025), operator returns turn negative (-$50 to -$70/acre), forcing dependence on USDA ARC/PLC subsidy bailouts and off-farm employment.",
    },
    {
        "id": "contract_poultry_cafo",
        "title": "Captive Contract Poultry Grower (CAFO Broilers)",
        "sector": "Livestock & Poultry Integration",
        "gross_farm_gate": 100.0,
        "retail_context": "Out of a $15 whole chicken or $100 meat bill, farmer receives $11.20 and nets ~$1.68 (~5¢ per bird).",
        "expenses": [
            {
                "name": "Mortgage Debt on $2M+ Barns",
                "amount": 45.00,
                "pct": 45.0,
                "beneficiaries": "Commercial Agricultural Banks, SBA Lenders",
                "color": "#94a3b8",
            },
            {
                "name": "Propane Heat & Electricity (Tunnel Fans)",
                "amount": 23.00,
                "pct": 23.0,
                "beneficiaries": "Utility Monopolies, Propane Distributors",
                "color": "#f59e0b",
            },
            {
                "name": "Barn Maintenance, Litter & Repairs",
                "amount": 17.00,
                "pct": 17.0,
                "beneficiaries": "Ventilation Equipment Dealers, Shavings Suppliers",
                "color": "#64748b",
            },
        ],
        "net_farmer_income": 15.00,
        "net_farmer_pct": 15.0,
        "take_home_notes": "Integrator (Tyson/Pilgrim's) owns the chicks, feed, and pricing. Grower carries 70%+ of total industry debt and all environmental liability, netting less than 5¢/bird for 70-hour workweeks.",
    },
    {
        "id": "independent_community_farm",
        "title": "Independent Regenerative Family Farm & Food Co-op",
        "sector": "Direct-to-Consumer & Cooperative",
        "gross_farm_gate": 100.0,
        "retail_context": "Out of $100 spent at a food co-op or CSA, farmer receives $42.00–$72.00 and nets $27.30–$50.40.",
        "expenses": [
            {
                "name": "Equipment Care & Solar/Renewable Fuel",
                "amount": 15.00,
                "pct": 15.0,
                "beneficiaries": "Local Independent Mechanics, Rural Solar",
                "color": "#34d399",
            },
            {
                "name": "Land Equity & Watershed Reserve",
                "amount": 10.00,
                "pct": 10.0,
                "beneficiaries": "Family Land Trust & Conservation Fund",
                "color": "#0d9488",
            },
            {
                "name": "Soil Health, Cover Crops & Organic Seed",
                "amount": 10.00,
                "pct": 10.0,
                "beneficiaries": "Regional Organic Seed Co-ops, Green Manures",
                "color": "#059669",
            },
            {
                "name": "Patented GMO Seed & Chemical Bills",
                "amount": 0.00,
                "pct": 0.0,
                "beneficiaries": "None (Eliminated through natural soil biology)",
                "color": "#cbd5e1",
            },
        ],
        "net_farmer_income": 65.00,
        "net_farmer_pct": 65.0,
        "take_home_notes": "By skipping patented inputs and selling direct or through cooperative wholesale, the farmer keeps 65% of gross revenue as living family income—over 25x more net profit per retail dollar than industrial agriculture.",
    },
]


@router.get("/farmland-ownership", response_model=FarmlandOwnershipStats)
def get_farmland_ownership():
    """Returns comprehensive statistics on US farmland tenure, tenancy, non-operator landlords, and elite landowners."""
    return FARMLAND_OWNERSHIP_DATA


@router.get("/farm-budgets")
def get_farm_budgets():
    """Returns comparative enterprise cost-of-production budgets and net farmer take-home pay."""
    return {
        "title": "Farm-Gate Cost Decomposition: What Does the Farmer Actually Pocket?",
        "description": "Deconstructs gross farm gate revenue into input supplier extraction vs. net household take-home income.",
        "comparisons": FARM_BUDGET_COMPARISONS,
    }

