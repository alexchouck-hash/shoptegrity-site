"""Shoptegrity Model Context Protocol (MCP) Server.

Provides tools for AI assistants to query brand integrity scores,
dollar flow splits, food chain sourcing, and local alternatives.
"""

from typing import Optional, Dict, Any, List
from sqlalchemy import or_
from api.app.db.session import SessionLocal, haversine_distance_km
from api.app.models.core import Brand, Entity, Alternative, Place, Maker, FlowProfile, BrandIntegrity
from api.app.services.scoring_service import score_entity


def lookup_brand(name: str) -> Dict[str, Any]:
    """Look up a brand's integrity scorecard, parent company, and citations."""
    db = SessionLocal()
    try:
        brand = db.query(Brand).filter(Brand.name.ilike(f"%{name}%")).first()
        if not brand:
            return {"error": f"Brand '{name}' not found in Shoptegrity database."}

        score_res = score_entity(brand.entity)
        return {
            "brand": brand.name,
            "parent_company": brand.entity.name,
            "ownership_type": brand.entity.ownership_type,
            "composite_score": score_res.composite_score,
            "confidence": score_res.confidence,
            "scorecard": {
                k: {
                    "score": v.value,
                    "status": v.status,
                    "explanation": v.explanation,
                    "citations": [e["source_url"] for e in v.evidence],
                }
                for k, v in score_res.dimensions.items()
            },
            "summary": (
                f"{brand.name} is owned by {brand.entity.name} ({brand.entity.ownership_type}). "
                f"Integrity Score: {score_res.composite_score}/100."
            ),
        }
    finally:
        db.close()


def find_alternatives(brand_name: str) -> Dict[str, Any]:
    """Find higher-integrity, ethical alternatives for a brand."""
    db = SessionLocal()
    try:
        brand = db.query(Brand).filter(Brand.name.ilike(f"%{brand_name}%")).first()
        if not brand:
            return {"error": f"Brand '{brand_name}' not found."}

        alts = (
            db.query(Alternative)
            .filter(Alternative.from_brand_id == brand.id, Alternative.editor_approved == True)
            .all()
        )

        cards = []
        for a in alts:
            target_score = score_entity(a.to_brand.entity)
            cards.append({
                "alternative_brand": a.to_brand.name,
                "parent_entity": a.to_brand.entity.name,
                "ownership_type": a.to_brand.entity.ownership_type,
                "composite_score": target_score.composite_score,
                "rationale": a.rationale,
                "price_band": a.price_band,
                "where_to_buy": a.where_to_buy,
                "savings_estimate": a.savings_estimate,
            })

        return {
            "source_brand": brand.name,
            "recommended_alternatives": cards,
            "summary": f"Found {len(cards)} verified higher-integrity alternatives for {brand.name}."
        }
    finally:
        db.close()


def find_local_businesses(lat: float, lon: float, category: Optional[str] = None, radius_km: float = 25.0) -> List[Dict[str, Any]]:
    """Find local businesses, co-ops, markets, and credit unions within radius."""
    db = SessionLocal()
    try:
        query = db.query(Place)
        if category:
            query = query.filter(Place.category == category)
        places = query.all()

        results = []
        for p in places:
            dist = haversine_distance_km(lat, lon, p.lat, p.lon)
            if dist <= radius_km:
                results.append({
                    "name": p.name,
                    "category": p.category,
                    "address": f"{p.address}, {p.city}, {p.state}",
                    "distance_km": dist,
                    "ownership_tier": p.ownership_tier,
                    "flags": p.flags or [],
                    "verified_locally": p.verified_locally,
                    "website": p.website,
                })
        results.sort(key=lambda x: x["distance_km"])
        return results
    finally:
        db.close()


def dollar_split_summary(category: str = "grocery") -> Dict[str, Any]:
    """Retrieve the USDA Food Dollar breakdown or spending flow split."""
    db = SessionLocal()
    try:
        flow = db.query(FlowProfile).filter(FlowProfile.spend_category_id == f"cat-{category}").all()
        return {
            "category": category,
            "profiles": [
                {
                    "title": f.display_title,
                    "type": f.option_type,
                    "summary": f.summary_text,
                    "nodes": f.nodes_json,
                }
                for f in flow
            ]
        }
    finally:
        db.close()


def search_top_brands(
    query: str = "",
    category: Optional[str] = None,
    min_grade: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """Search the top 2,000 brands database by name, sector, and minimum integrity grade."""
    db = SessionLocal()
    try:
        q = db.query(BrandIntegrity)
        if query:
            q = q.filter(
                or_(
                    BrandIntegrity.name.ilike(f"%{query}%"),
                    BrandIntegrity.parent_company.ilike(f"%{query}%"),
                )
            )
        if category and category != "All":
            q = q.filter(BrandIntegrity.category == category)
        if min_grade:
            grade_order = {"A+": 6, "A": 5, "B": 4, "C": 3, "D": 2, "F": 1}
            min_val = grade_order.get(min_grade, 1)
            valid_grades = [g for g, v in grade_order.items() if v >= min_val]
            q = q.filter(BrandIntegrity.grade.in_(valid_grades))

        total = q.count()
        matches = q.limit(limit).all()

        return {
            "total_matches": total,
            "returned_count": len(matches),
            "brands": [
                {
                    "name": b.name,
                    "category": b.category,
                    "parent_company": b.parent_company,
                    "grade": b.grade,
                    "composite_score": b.composite_score,
                    "worker_wages_pct": f"{b.worker_wages_pct}%",
                    "shareholder_extraction_pct": f"{b.shareholder_extraction_pct}%",
                    "labor_exploitation_rating": b.labor_exploitation_rating,
                    "waste_rating": b.waste_rating,
                    "swap_recommendation": b.swap_name,
                }
                for b in matches
            ],
        }
    finally:
        db.close()


def lookup_brand_integrity(brand_name: str) -> Dict[str, Any]:
    """Retrieve in-depth integrity metrics: worker vs executive vs shareholder splits, labor exploitation, and waste."""
    db = SessionLocal()
    try:
        brand = (
            db.query(BrandIntegrity)
            .filter(BrandIntegrity.name.ilike(f"%{brand_name}%"))
            .first()
        )
        if not brand:
            return {"error": f"Brand '{brand_name}' not found in the 2,000-brand database."}

        return {
            "name": brand.name,
            "category": brand.category,
            "parent_company": brand.parent_company,
            "ownership_type": brand.ownership_type,
            "composite_score": brand.composite_score,
            "grade": brand.grade,
            "dollar_flow_split": {
                "worker_wages_pct": brand.worker_wages_pct,
                "executive_compensation_pct": brand.exec_comp_pct,
                "shareholder_buybacks_dividends_pct": brand.shareholder_extraction_pct,
                "advertising_marketing_pct": brand.marketing_ads_pct,
                "cost_of_goods_supply_pct": brand.cogs_supply_pct,
                "retained_operations_pct": brand.retained_operations_pct,
                "key_takeaway": (
                    f"At {brand.name}, {brand.shareholder_extraction_pct}% of revenue flows to shareholders "
                    f"and {brand.marketing_ads_pct}% to ads, compared to {brand.worker_wages_pct}% for frontline workers."
                ),
            },
            "labor_exploitation": {
                "rating": brand.labor_exploitation_rating,
                "sweatshop_risk": brand.sweatshop_risk,
                "osha_violations_count": brand.osha_violations_count,
                "nlrb_complaints_count": brand.nlrb_complaints_count,
                "living_wage_certified": brand.living_wage_certified,
                "summary": brand.labor_summary,
            },
            "waste_and_packaging": {
                "waste_rating": brand.waste_rating,
                "packaging_type": brand.packaging_type,
                "repairability_score": brand.repairability_score,
                "landfill_diverted_pct": brand.landfill_diverted_pct,
                "summary": brand.waste_summary,
            },
            "recommended_swap": {
                "swap_name": brand.swap_name,
                "swap_slug": brand.swap_slug,
                "swap_rationale": brand.swap_rationale,
            },
        }
    finally:
        db.close()


def rate_major_retailers() -> Dict[str, Any]:
    """Retrieve scorecards, shareholder extraction, worker wages, and swaps for major retailers (Target, Walmart, Costco, etc.)."""
    db = SessionLocal()
    try:
        retailers = (
            db.query(BrandIntegrity)
            .filter(BrandIntegrity.is_major_retailer == True)
            .order_by(BrandIntegrity.composite_score.desc())
            .all()
        )
        return {
            "title": "Major Retailers Integrity Scorecard & Swaps",
            "count": len(retailers),
            "retailers": [
                {
                    "name": r.name,
                    "grade": r.grade,
                    "score": r.composite_score,
                    "parent_company": r.parent_company,
                    "worker_wages": f"{r.worker_wages_pct}%",
                    "shareholder_extraction": f"{r.shareholder_extraction_pct}%",
                    "labor_rating": r.labor_exploitation_rating,
                    "waste_rating": r.waste_rating,
                    "packaging": r.packaging_type,
                    "easy_swap": r.swap_name,
                    "swap_rationale": r.swap_rationale,
                    "details": r.retailer_details or {},
                }
                for r in retailers
            ],
        }
    finally:
        db.close()


def get_retailer_swaps(retailer_name: str) -> Dict[str, Any]:
    """Retrieve direct ethical swaps for a major shopping retailer (e.g. Walmart -> WinCo Foods, Home Depot -> Ace Hardware)."""
    db = SessionLocal()
    try:
        ret = (
            db.query(BrandIntegrity)
            .filter(BrandIntegrity.name.ilike(f"%{retailer_name}%"), BrandIntegrity.is_major_retailer == True)
            .first()
        )
        if not ret:
            return {"error": f"Major retailer '{retailer_name}' not found. Available: Walmart, Target, Costco, Amazon, Kroger, Dollar General, The Home Depot."}

        return {
            "current_retailer": ret.name,
            "grade": ret.grade,
            "integrity_score": ret.composite_score,
            "shareholder_extraction": f"{ret.shareholder_extraction_pct}% of revenue",
            "worker_wages": f"{ret.worker_wages_pct}% of revenue",
            "recommended_swap": ret.swap_name,
            "swap_rationale": ret.swap_rationale,
            "retailer_details": ret.retailer_details or {},
        }
    finally:
        db.close()


def lookup_parent_company(query: str) -> Dict[str, Any]:
    """Identify the corporate parent, ownership structure, subterfuge context, and ethical swap for any brand or product."""
    from api.app.services.parent_lookup_service import parent_service

    match = parent_service.lookup(query)
    if not match:
        return {"error": f"No parent company record found for query: '{query}'"}

    return {
        "query": query,
        "matched_name": match["name"],
        "item_type": match["item_type"],
        "category": match["category"],
        "parent_company": match["parent_company"],
        "ultimate_parent": match["ultimate_parent"],
        "ownership_type": match["ownership_type"],
        "ticker_or_jurisdiction": match["ticker_or_jurisdiction"],
        "is_surprising_or_subterfuge": match["is_surprising_or_subterfuge"],
        "subterfuge_details": match["subterfuge_details"],
        "top_10_percent_enrichment_pct": f"{match['top_10_percent_enrichment_pct']}%",
        "ethical_swap_recommendation": match["ethical_swap_recommendation"],
    }


def get_brand_parent_feed(query: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
    """Search or browse the 1,000+ brand and product parent company data feed."""
    from api.app.services.parent_lookup_service import parent_service

    res = parent_service.get_feed(q=query, limit=limit)
    return {
        "total_matches": res["total"],
        "count": len(res["results"]),
        "items": [
            {
                "name": item["name"],
                "parent_company": item["parent_company"],
                "ultimate_parent": item["ultimate_parent"],
                "ownership_type": item["ownership_type"],
                "is_surprising": item["is_surprising_or_subterfuge"],
                "ethical_swap": item["ethical_swap_recommendation"],
            }
            for item in res["results"]
        ],
    }

