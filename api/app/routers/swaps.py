from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.app.db.session import get_db
from api.app.models.core import SpendCategory, Alternative
from api.app.schemas.domain import SpendCategoryRead, AlternativeCard
from api.app.services.scoring_service import score_entity

router = APIRouter(prefix="/v1/swaps", tags=["Swap Guide"])


@router.get("", response_model=List[SpendCategoryRead])
def list_swap_categories(db: Session = Depends(get_db)):
    """Returns household spending categories ranked by ease of swap and financial impact."""
    categories = db.query(SpendCategory).order_by(SpendCategory.tier, SpendCategory.avg_annual_spend.desc()).all()
    return categories


@router.get("/{slug}")
def get_swap_guide_detail(slug: str, db: Session = Depends(get_db)):
    """Returns a full swap guide for a spend category with steps, limits, and alternatives."""
    cat = db.query(SpendCategory).filter(SpendCategory.slug == slug).first()
    if not cat:
        raise HTTPException(status_code=404, detail=f"Category '{slug}' not found")

    alternatives = (
        db.query(Alternative)
        .filter(Alternative.spend_category_id == cat.id, Alternative.editor_approved == True)
        .all()
    )

    alt_cards = []
    for alt in alternatives:
        target_score = score_entity(alt.to_brand.entity)
        alt_cards.append(
            AlternativeCard(
                id=alt.id,
                brand_name=alt.to_brand.name,
                brand_slug=alt.to_brand.slug,
                parent_name=alt.to_brand.entity.name,
                ownership_type=alt.to_brand.entity.ownership_type,
                composite_score=target_score.composite_score,
                rationale=alt.rationale,
                price_band=alt.price_band,
                where_to_buy=alt.where_to_buy,
                savings_estimate=alt.savings_estimate,
            )
        )

    # Step by step guides for launch categories
    guides = {
        "banking": {
            "title": "Switching from Megabanks to Community Credit Unions",
            "estimated_annual_dollars_rerouted": "$4,200 (deposits, fees, and lending capital)",
            "average_savings": "$120/yr in reduced bank maintenance and ATM fees",
            "steps": [
                "Find a local or community development credit union (CDFI) using the Local Directory.",
                "Open a no-fee checking and high-yield savings account.",
                "Update direct deposit with your employer.",
                "Switch automatic bill payments and subscriptions (keep original account open for 30 days buffer).",
                "Close megabank account and request a balance cashier's check.",
            ],
            "limits": "Credit unions have fewer physical branches nationwide, though most participate in the 30,000+ CO-OP Shared Branch and ATM network.",
        },
        "grocery": {
            "title": "Rerouting the Food Cart to Co-ops and Regional Growers",
            "estimated_annual_dollars_rerouted": "$3,600 / household",
            "average_savings": "Neutral to +$150/yr using bulk bins and seasonal produce",
            "steps": [
                "Locate your nearest food cooperative or weekly farmers market.",
                "Purchase pantry staples (grains, beans, oats, spices) from the co-op bulk section (often 30-50% cheaper than packaged brands).",
                "Join a seasonal CSA (Community Supported Agriculture) box for direct weekly farm vegetables.",
                "Swap multinational snack and packaged brands for employee-owned (ESOP) and B-Corp alternatives (e.g. King Arthur Baking, Bob's Red Mill).",
            ],
            "limits": "Certain off-season fruits and specialty products will still rely on longer supply chains.",
        },
        "clothing": {
            "title": "Breaking the Fast Fashion Cycle",
            "estimated_annual_dollars_rerouted": "$1,400 / household",
            "average_savings": "$400/yr by prioritizing secondhand, durable essentials, and repair",
            "steps": [
                "Follow the apparel ladder: wear existing clothes longer, repair zippers/hems, shop thrift/consignment.",
                "When buying new, prioritize mission-locked brands with transparent supply chains and living wages.",
                "Check garment tag composition: avoid virgin polyester and synthetic fast-fashion blends.",
            ],
            "limits": "Technical gear and specialty footwear have fewer 100% cooperative alternatives.",
        },
    }

    guide_data = guides.get(cat.slug, {
        "title": f"Ethical Shopping Guide: {cat.name}",
        "estimated_annual_dollars_rerouted": f"${int(cat.avg_annual_spend)} / yr",
        "average_savings": "Saves money through longevity and reduced waste" if cat.saves_money else "Price competitive",
        "steps": [
            f"Audit your top recurring purchases in {cat.name.lower()}.",
            "Identify member-owned, local, or B-Corp alternatives from our directory.",
            "Test one swap this month.",
        ],
        "limits": "Availability varies by geographic region.",
    })

    return {
        "category": SpendCategoryRead.model_validate(cat),
        "guide": guide_data,
        "recommended_alternatives": alt_cards,
    }
