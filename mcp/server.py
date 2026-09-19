"""Shoptegrity Model Context Protocol (MCP) Server.

Provides tools for AI assistants to query brand integrity scores,
dollar flow splits, food chain sourcing, and local alternatives.
"""

from typing import Optional, Dict, Any, List
from api.app.db.session import SessionLocal, haversine_distance_km
from api.app.models.core import Brand, Entity, Alternative, Place, Maker, FlowProfile
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
