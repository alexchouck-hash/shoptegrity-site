from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.app.db.session import get_db
from api.app.models.core import SpendCategory, Alternative
from api.app.schemas.domain import SpendCategoryRead, AlternativeCard
from api.app.services.scoring_service import score_entity
from api.app.services.citation import cited_ownership_name, cited_ownership_type

router = APIRouter(prefix="/v1/swaps", tags=["Swap Guide"])

# Shown wherever a figure, score or claim has no cited source (owner policy: sourced or withheld).
WITHHELD = "Withheld: no cited source yet"


@router.get("", response_model=List[SpendCategoryRead])
def list_swap_categories(db: Session = Depends(get_db)):
    """Returns household spending categories by tier. Spend figures are withheld until cited."""
    categories = db.query(SpendCategory).order_by(SpendCategory.tier, SpendCategory.name).all()
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
    best_alts = []
    better_alts = []
    for alt in alternatives:
        target_score = score_entity(alt.to_brand.entity)
        card = AlternativeCard(
            id=alt.id,
            brand_name=alt.to_brand.name,
            brand_slug=alt.to_brand.slug,
            parent_name=cited_ownership_name(alt.to_brand.entity),
            ownership_type=cited_ownership_type(alt.to_brand.entity),
            composite_score=target_score.composite_score,
            rationale=None,  # withheld until cited (R1)
            price_band=None,  # withheld until cited (R1)
            where_to_buy=None,  # withheld until cited (R1)
            savings_estimate=None,  # dollar savings are withheld until each has a cited source (R1)
            swap_tier=getattr(alt, "swap_tier", "best"),
            similarity_notes=getattr(alt, "similarity_notes", None),
        )
        alt_cards.append(card)
        if getattr(alt, "swap_tier", "best") == "better":
            better_alts.append(card)
        else:
            best_alts.append(card)

    # Step by step guides with Best (high ethical standard) & Better (similar price/experience).
    # Scores on category-level options are Shoptegrity opinions and are labelled as such.
    # Options that name real companies carry no score until one is computed from cited inputs.
    guides = {
        "banking": {
            "title": "Switching from Megabanks to Community Credit Unions",
            "estimated_annual_dollars_rerouted": WITHHELD,
            "average_savings": WITHHELD,
            "best_swap": {
                "name": "Local Community Development Credit Union (CDFI) / Clean-Energy CU",
                "badge": "Best Swap",
                "tier_label": "High Ethical Standard",
                "score": "Shoptegrity opinion: 98/100 (Grade A+)",
                "price_level": "$$ (Check each account's fee schedule)",
                "experience": "May differ: many credit unions use shared branch and ATM networks rather than their own storefronts.",
                "cost_impact": "Fees and loan rates vary by institution. Compare the fee schedule before switching.",
                "rationale": "A member-owned, not-for-profit cooperative. Check the credit union's charter and its own disclosures before moving money.",
            },
            "better_swap": {
                "name": "Regional Credit Union / Community Bank",
                "badge": "Better Swap",
                "tier_label": "Similar Price & Experience",
                "score": "Shoptegrity opinion: 82/100 (Grade B+)",
                "price_level": "$ (Check each account's fee schedule)",
                "experience": "Familiar drop-in. Typical features to confirm: mobile app, direct deposit, bill pay, debit card, and ATM access.",
                "cost_impact": "Compare monthly fees, overdraft terms, and savings rates on the institution's current disclosure sheet.",
                "rationale": "Keeps everyday banking familiar while moving deposits to a locally based institution. Confirm the details with the institution itself.",
            },
            "steps": [
                "Find a local or community development credit union (CDFI) using the Local Directory.",
                "Open a checking account and a savings account, comparing fee schedules first.",
                "Update direct deposit with your employer.",
                "Switch automatic bill payments and subscriptions (keep original account open for a 30-day buffer).",
                "Close the old bank account and request a balance check.",
            ],
            "limits": "Credit unions often have fewer physical branches. Many join shared branch and ATM networks. Check which network your credit union uses.",
        },
        "grocery": {
            "title": "Rerouting the Food Cart to Co-ops and Regional Growers",
            "estimated_annual_dollars_rerouted": WITHHELD,
            "average_savings": WITHHELD,
            "best_swap": {
                "name": "Member-Owned Food Cooperatives & Direct Farm CSAs",
                "badge": "Best Swap",
                "tier_label": "High Ethical Standard",
                "score": "Shoptegrity opinion: 96/100 (Grade A+)",
                "price_level": "$$ - $$$ (varies by store and season)",
                "experience": "May differ: weekly produce box pickup or co-op aisles with seasonal rotations.",
                "cost_impact": "Specialty items may cost more. Bulk-bin buying can lower the cost of pantry staples. Compare unit prices.",
                "rationale": "Co-ops are owned by their members. Confirm each store's governance and sourcing in its own published documents.",
            },
            "better_swap": {
                "name": "Discount grocery formats (category)",
                "badge": "Better Swap",
                "tier_label": "Similar Price & Experience",
                "score": WITHHELD,
                "price_level": "$ (Compare unit prices at your local store)",
                "experience": "Typical format: standard supermarket aisles and checkout. Confirm the store's current format.",
                "cost_impact": "Compare prices on your usual items before switching.",
                "rationale": "Category-level option. Named companies, their ownership, wages and prices are withheld until sourced.",
            },
            "steps": [
                "Locate your nearest food cooperative or weekly farmers market.",
                "Buy pantry staples (grains, beans, oats, spices) from the co-op bulk section, and compare unit prices with packaged brands.",
                "Join a seasonal CSA (Community Supported Agriculture) box for direct weekly farm vegetables.",
                "Swap packaged brands for alternatives whose ownership you can confirm from their own disclosures .",
            ],
            "limits": "Certain off-season fruits and specialty products will still rely on longer supply chains.",
        },
        "clothing": {
            "title": "Breaking the Fast Fashion Cycle",
            "estimated_annual_dollars_rerouted": WITHHELD,
            "average_savings": WITHHELD,
            "best_swap": {
                "name": "Durable-goods brands & local tailors (category)",
                "badge": "Best Swap",
                "tier_label": "High Ethical Standard",
                "score": WITHHELD,
                "price_level": "$$$ (higher upfront cost per item)",
                "experience": "May differ: fewer impulse buys, a smaller wardrobe built around durable pieces, and local repair services.",
                "cost_impact": "Upfront cost is higher per piece. Compare cost per wear over the garment's life, not the sticker price.",
                "rationale": "Look for brands that publish their repair, governance and supply-chain policies. Claims about named brands are withheld until sourced.",
            },
            "better_swap": {
                "name": "Secondhand resale platforms & natural-fiber basics (category)",
                "badge": "Better Swap",
                "tier_label": "Similar Price & Experience",
                "score": WITHHELD,
                "price_level": "$ - $$ (compare prices with your usual brands)",
                "experience": "Familiar drop-in: online shopping, doorstep delivery, and standard clothing categories.",
                "cost_impact": "Secondhand listings are often priced below new retail. Compare listings before buying.",
                "rationale": "Extends the life of existing garments and offers basics made with organic cotton. Check each brand's certifications before buying.",
            },
            "steps": [
                "Follow the apparel ladder: wear existing clothes longer, repair zippers and hems, and shop thrift or consignment.",
                "When buying new, prioritize brands that publish supply-chain and wage information you can verify.",
                "Check garment tag composition: avoid virgin polyester and synthetic fast-fashion blends.",
            ],
            "limits": "Technical gear and specialty footwear may have fewer cooperative alternatives.",
        },
        "insurance": {
            "title": "Policyholder-Owned Mutual Insurance",
            "estimated_annual_dollars_rerouted": WITHHELD,
            "average_savings": WITHHELD,
            "best_swap": {
                "name": "Member-Owned Fraternal Benefit Societies & Regional Farm Mutuals",
                "badge": "Best Swap",
                "tier_label": "High Ethical Standard",
                "score": "Shoptegrity opinion: 92/100 (Grade A)",
                "price_level": "$$ (compare quotes; some mutuals pay member dividends)",
                "experience": "May differ: regional agent relationships, member voting, and claims handled through a local office.",
                "cost_impact": "Premiums vary by location and insurer. Compare quotes and the dividend policy in writing.",
                "rationale": "Mutual insurers are owned by their policyholders rather than public shareholders. Confirm a company's legal form with your state insurance regulator.",
            },
            "better_swap": {
                "name": "Mutual insurers (category)",
                "badge": "Better Swap",
                "tier_label": "Similar Price & Experience",
                "score": WITHHELD,
                "price_level": "$$ (compare quotes with other insurers)",
                "experience": "Familiar drop-in: online claims app, quote comparison, and automatic payments.",
                "cost_impact": "Compare premiums directly. Price varies by driver, home and location.",
                "rationale": "Confirm each company's structure before switching. Claims about named companies are withheld until sourced.",
            },
            "steps": [
                "Review current auto and homeowners or renters insurance coverage declarations.",
                "Request quotes from mutual insurers in your area.",
                "Confirm that the insurer operates as a policyholder-owned mutual rather than a publicly traded stock company.",
                "Switch at renewal to avoid cancellation penalties.",
            ],
            "limits": "Certain high-risk coastal or wildfire zones may have limited underwriting capacity among mutuals.",
        },
        "hardware": {
            "title": "Supporting Independent Hardware Cooperatives & Circular Repair",
            "estimated_annual_dollars_rerouted": WITHHELD,
            "average_savings": WITHHELD,
            "best_swap": {
                "name": "Independent Hardware Cooperatives & Community Tool Libraries",
                "badge": "Best Swap",
                "tier_label": "High Ethical Standard",
                "score": "Shoptegrity opinion: 94/100 (Grade A)",
                "price_level": "$ - $$ (tool libraries may lend tools free of charge)",
                "experience": "May differ: borrow a power tool from a tool library instead of buying single-use equipment.",
                "cost_impact": "Borrowing avoids buying tools you use rarely. Hardware prices vary by store, so compare before buying.",
                "rationale": "Member-owned hardware cooperatives and tool libraries keep purchasing and resource sharing local. Check each store's ownership before assuming.",
            },
            "better_swap": {
                "name": "Independent Lumberyards & Regional Hardware Stores",
                "badge": "Better Swap",
                "tier_label": "Similar Price & Experience",
                "score": "Shoptegrity opinion: 80/100 (Grade B+)",
                "price_level": "$$ (compare prices with big-box stores)",
                "experience": "Typical format: fastener and paint aisles, tools, and lumber yard service. Confirm each store's current range.",
                "cost_impact": "Prices are competitive on many common supplies. Compare before you buy.",
                "rationale": "Keeps purchases with regional, independently owned merchants.",
            },
            "steps": [
                "Map your local independent hardware store or family lumberyard.",
                "Check whether your city has a Community Tool Lending Library or a Habitat for Humanity ReStore.",
                "Buy hardware from bulk bins where available, rather than single-use blister packs.",
            ],
            "limits": "Large-scale specialty industrial construction supplies may require dedicated commercial distributors.",
        },
    }

    guide_data = guides.get(cat.slug, {
        "title": f"Ethical Shopping Guide: {cat.name}",
        "estimated_annual_dollars_rerouted": WITHHELD,
        "average_savings": WITHHELD,
        "best_swap": {
            "name": "Independent Cooperative or Mission-Locked Maker",
            "badge": "Best Swap",
            "tier_label": "High Ethical Standard",
            "score": "Shoptegrity opinion: 90+/100 (Grade A)",
            "price_level": "$$ - $$$",
            "experience": "May differ in distribution format.",
            "cost_impact": "Cost may be higher upfront. Compare before buying.",
            "rationale": "Supports democratic ownership, worker equity, and transparent sourcing.",
        },
        "better_swap": {
            "name": "Employee-Owned or B Corp Alternative",
            "badge": "Better Swap",
            "tier_label": "Similar Price & Experience",
            "score": "Shoptegrity opinion: 75-85/100 (Grade B / B+)",
            "price_level": "$ - $$",
            "experience": "Familiar drop-in replacement with similar everyday convenience. Check each company's status.",
            "cost_impact": "Compare prices before switching.",
            "rationale": "An accessible stepping stone for people who want a closer match to their current habits.",
        },
        "steps": [
            f"Audit your top recurring purchases in {cat.name.lower()}.",
            "Identify member-owned, local, or B Corp alternatives from our directory.",
            "Test one swap this month.",
        ],
        "limits": "Availability varies by geographic region.",
    })

    return {
        "category": SpendCategoryRead.model_validate(cat),
        "guide": guide_data,
        "recommended_alternatives": alt_cards,
        "best_alternatives": best_alts,
        "better_alternatives": better_alts,
    }
