from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.app.db.session import get_db, haversine_distance_km
from api.app.models.core import Maker, Place, SpendCategory
from api.app.schemas.domain import MakerSummary, PlaceSummary, FoodDollarSplit

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

