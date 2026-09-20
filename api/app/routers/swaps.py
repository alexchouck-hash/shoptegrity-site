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
    best_alts = []
    better_alts = []
    for alt in alternatives:
        target_score = score_entity(alt.to_brand.entity)
        card = AlternativeCard(
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
            swap_tier=getattr(alt, "swap_tier", "best"),
            similarity_notes=getattr(alt, "similarity_notes", None),
        )
        alt_cards.append(card)
        if getattr(alt, "swap_tier", "best") == "better":
            better_alts.append(card)
        else:
            best_alts.append(card)

    # Step by step guides with Best (high ethical standard) & Better (similar price/experience)
    guides = {
        "banking": {
            "title": "Switching from Megabanks to Community Credit Unions",
            "estimated_annual_dollars_rerouted": "$4,200 (deposits, fees, and lending capital)",
            "average_savings": "$120/yr in reduced bank maintenance and ATM fees",
            "best_swap": {
                "name": "Local Community Development Credit Union (CDFI) / Clean-Energy CU",
                "badge": "Best Swap",
                "tier_label": "High Ethical Standard",
                "score": "98/100 (Grade A+)",
                "price_level": "$$ (Competitive loans / waived fees)",
                "experience": "May differ: relies on 30,000+ shared CO-OP branches/ATMs rather than mega-storefronts.",
                "cost_impact": "Cost might be higher for niche wealth services, but eliminates predatory fees.",
                "rationale": "100% member-owned nonprofit cooperative. Every deposit dollar recirculates into local community mortgages, affordable housing, and regional green businesses with zero fossil fuel underwriting.",
            },
            "better_swap": {
                "name": "Regional Credit Union / High-Yield Community Bank",
                "badge": "Better Swap",
                "tier_label": "Similar Price & Experience",
                "score": "82/100 (Grade B+)",
                "price_level": "$ (Zero maintenance fees)",
                "experience": "Familiar drop-in: identical modern mobile app, instant transfers, Apple Pay, nationwide fee-free ATMs.",
                "cost_impact": "Matches or beats megabank costs: no monthly checking fees, higher savings APY.",
                "rationale": "Maintains the frictionless daily banking convenience you are used to while terminating the endless cycle of megabank overdraft fines, fake account scandals, and Wall Street extraction.",
            },
            "steps": [
                "Find a local or community development credit union (CDFI) using the Local Directory.",
                "Open a no-fee checking and high-yield savings account.",
                "Update direct deposit with your employer.",
                "Switch automatic bill payments and subscriptions (keep original account open for 30 days buffer).",
                "Close megabank account and request a balance cashier's check.",
            ],
            "limits": "Credit unions have fewer private physical storefronts, though most participate in the 30,000+ CO-OP Shared Branch and ATM network.",
        },
        "grocery": {
            "title": "Rerouting the Food Cart to Co-ops and Regional Growers",
            "estimated_annual_dollars_rerouted": "$3,600 / household",
            "average_savings": "Neutral to +$150/yr using bulk bins and seasonal produce",
            "best_swap": {
                "name": "Member-Owned Food Cooperatives & Direct Farm CSAs",
                "badge": "Best Swap",
                "tier_label": "High Ethical Standard",
                "score": "96/100 (Grade A+)",
                "price_level": "$$ - $$$ (True cost of sustainable farming)",
                "experience": "May differ: weekly produce box pickup or neighborhood co-op aisles with seasonal local rotations.",
                "cost_impact": "Cost might be higher for specialty items, but saves 30-50% on pantry staples via bulk bin refills.",
                "rationale": "Democratically owned by shoppers and workers. Over 40% of shelf items come from regional growers (vs 5% at mega-chains), keeping 100% of profits in local soil.",
            },
            "better_swap": {
                "name": "WinCo Foods (100% ESOP) & Aldi",
                "badge": "Better Swap",
                "tier_label": "Similar Price & Experience",
                "score": "78-85/100 (Grade B / B+)",
                "price_level": "$ (Matches or beats Walmart pricing)",
                "experience": "Familiar drop-in: standard grocery carts, full supermarket selection, rapid checkout.",
                "cost_impact": "Zero cost increase: matches or beats conventional grocery chain prices on milk, eggs, produce, and pantry staples.",
                "rationale": "WinCo is 100% employee-owned (ESOP) where cashier and warehouse staff build pensions of $500k+. Aldi pays above-average living wages and runs efficient, low-waste stores.",
            },
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
            "best_swap": {
                "name": "Repair-For-Life Brands (Patagonia, Darn Tough) & Local Tailors",
                "badge": "Best Swap",
                "tier_label": "High Ethical Standard",
                "score": "95/100 (Grade A+)",
                "price_level": "$$$ (Heirloom investment)",
                "experience": "May differ: fewer impulse buys, intentional wardrobe curation, lifetime warranty repairs.",
                "cost_impact": "Upfront cost is higher per piece, but delivers dramatic long-term savings by lasting 5-10+ years.",
                "rationale": "Mission-locked ownership (purpose trusts and worker cooperatives) that guarantees living wages, transparent supply chains, organic materials, and free lifetime repairs.",
            },
            "better_swap": {
                "name": "Curated Secondhand Thrift (Poshmark, ThredUp) & Certified B-Corp Basics (Pact)",
                "badge": "Better Swap",
                "tier_label": "Similar Price & Experience",
                "score": "80/100 (Grade B+)",
                "price_level": "$ - $$ (Affordable budget friendly)",
                "experience": "Familiar drop-in: seamless online app shopping, doorstep delivery, standard clothing categories.",
                "cost_impact": "Matches fast-fashion prices: secondhand thrift cuts garment costs by 50-70% while buying existing textiles.",
                "rationale": "Circulates existing garments or provides GOTS-certified organic cotton basics at budget prices, keeping dollars out of ultra-fast-fashion sweatshops.",
            },
            "steps": [
                "Follow the apparel ladder: wear existing clothes longer, repair zippers/hems, shop thrift/consignment.",
                "When buying new, prioritize mission-locked brands with transparent supply chains and living wages.",
                "Check garment tag composition: avoid virgin polyester and synthetic fast-fashion blends.",
            ],
            "limits": "Technical gear and specialty footwear have fewer 100% cooperative alternatives.",
        },
        "insurance": {
            "title": "Policyholder-Owned Mutual Insurance",
            "estimated_annual_dollars_rerouted": "$3,100 / household",
            "average_savings": "$180/yr in policyholder dividend returns and fair claims payouts",
            "best_swap": {
                "name": "Member-Owned Fraternal Benefit Societies & Regional Farm Mutuals",
                "badge": "Best Swap",
                "tier_label": "High Ethical Standard",
                "score": "92/100 (Grade A)",
                "price_level": "$$ (Competitive rates with annual member dividends)",
                "experience": "May differ: regional agent relationships, communal member voting, non-corporate claims handling.",
                "cost_impact": "Cost might be slightly higher upfront in certain zip codes, but policyholder dividends return surplus cash.",
                "rationale": "Pure mutual structure where 100% of surplus belongs to policyholders. No hedge funds demanding claim denials to boost quarterly EPS.",
            },
            "better_swap": {
                "name": "National Mutual Insurers (Amica Mutual, Nationwide Mutual)",
                "badge": "Better Swap",
                "tier_label": "Similar Price & Experience",
                "score": "82/100 (Grade B+)",
                "price_level": "$$ (Directly price-competitive with GEICO/Progressive)",
                "experience": "Familiar drop-in: 24/7 online claims app, instant quote comparison, paperless auto-pay.",
                "cost_impact": "Identical premium pricing to publicly traded insurers, often with higher customer satisfaction.",
                "rationale": "Policyholder-owned mutuals without public stock market pressure, eliminating the incentive to delay and deny claims for stock buybacks.",
            },
            "steps": [
                "Review current auto and homeowners/renters insurance policy coverage declarations.",
                "Request quotes from top-rated mutual insurers (Amica, regional mutuals).",
                "Confirm that the insurer operates as a policyholder-owned mutual rather than a publicly traded stock entity.",
                "Switch policy upon renewal to capture clean underwriting and avoid cancellation penalties.",
            ],
            "limits": "Certain high-risk coastal or wildfire zones have limited underwriting capacity among mutuals.",
        },
        "hardware": {
            "title": "Supporting Independent Hardware Cooperatives & Circular Repair",
            "estimated_annual_dollars_rerouted": "$1,500 / household",
            "average_savings": "Neutral to +$200/yr through tool lending and longevity",
            "best_swap": {
                "name": "Ace Hardware (Retailer-Owned Co-op) & Community Tool Libraries",
                "badge": "Best Swap",
                "tier_label": "High Ethical Standard",
                "score": "94/100 (Grade A)",
                "price_level": "$ - $$ (Free borrowing for tools; standard retail hardware)",
                "experience": "May differ: borrowing power tools for free from a tool library instead of purchasing single-use equipment.",
                "cost_impact": "Saves hundreds per year on tools; individual hardware items match Home Depot prices.",
                "rationale": "Over 5,000 Ace Hardware stores are 100% independently owned by local merchants. Tool lending libraries enable zero-waste community resource sharing.",
            },
            "better_swap": {
                "name": "True Value / Regional Independent Lumberyards",
                "badge": "Better Swap",
                "tier_label": "Similar Price & Experience",
                "score": "80/100 (Grade B+)",
                "price_level": "$$ (Matches big-box home improvement prices)",
                "experience": "Familiar drop-in: wide aisles, complete DIY fastener and paint aisles, drive-through lumber yard.",
                "cost_impact": "Price-competitive on common supplies, fasteners, plumbing fittings, and tools.",
                "rationale": "Keeps dollars with regional hardware merchants and independent family yards rather than funding billion-dollar Wall Street share repurchases.",
            },
            "steps": [
                "Map your local Ace Hardware or independent family lumberyard.",
                "Check if your city has a Community Tool Lending Library or Habitat for Humanity ReStore.",
                "Buy bulk hardware, screws, and fittings from open bins rather than single-use plastic blister packs.",
            ],
            "limits": "Large-scale specialty industrial construction supplies may require dedicated commercial distributors.",
        },
    }

    guide_data = guides.get(cat.slug, {
        "title": f"Ethical Shopping Guide: {cat.name}",
        "estimated_annual_dollars_rerouted": f"${int(cat.avg_annual_spend)} / yr",
        "average_savings": "Saves money through longevity and reduced waste" if cat.saves_money else "Price competitive",
        "best_swap": {
            "name": "Independent Cooperative or Mission-Locked Maker",
            "badge": "Best Swap",
            "tier_label": "High Ethical Standard",
            "score": "90+/100 (Grade A)",
            "price_level": "$$ - $$$",
            "experience": "May differ in distribution format; maximizes worker and community welfare.",
            "cost_impact": "Cost might be higher upfront, but delivers superior durability and zero exploitation.",
            "rationale": "Supports democratic ownership, worker equity, and transparent sourcing.",
        },
        "better_swap": {
            "name": "Employee-Owned (ESOP) or Certified B-Corp Alternative",
            "badge": "Better Swap",
            "tier_label": "Similar Price & Experience",
            "score": "75-85/100 (Grade B / B+)",
            "price_level": "$ - $$",
            "experience": "Familiar drop-in replacement with similar pricing and everyday convenience.",
            "cost_impact": "Matches conventional price point.",
            "rationale": "Accessible stepping stone that avoids predatory practices and Wall Street extraction.",
        },
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
        "best_alternatives": best_alts,
        "better_alternatives": better_alts,
    }
