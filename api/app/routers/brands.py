from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from api.app.db.session import get_db
from api.app.models.core import Brand, Entity, Alternative, Evidence
from api.app.schemas.domain import BrandSummary, BrandDetail, AlternativeCard, EntityScoreSummary, DimensionScoreSchema, EvidenceSchema
from api.app.services.scoring_service import score_entity

router = APIRouter(prefix="/v1/brands", tags=["Brands & Scorecards"])


@router.get("", response_model=List[BrandSummary])
def list_or_search_brands(
    q: Optional[str] = Query(None, description="Search by brand name or parent company"),
    category: Optional[str] = Query(None, description="Filter by category tag"),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Brand).join(Entity, Brand.entity_id == Entity.id)
    if q:
        search_pattern = f"%{q.lower()}%"
        query = query.filter(
            or_(
                Brand.name.ilike(search_pattern),
                Entity.name.ilike(search_pattern),
            )
        )

    brands = query.limit(limit).all()
    results = []
    for b in brands:
        score_res = score_entity(b.entity)
        results.append(
            BrandSummary(
                id=b.id,
                name=b.name,
                slug=b.slug,
                description=b.description,
                category_tags=b.category_tags or [],
                parent_company_name=b.entity.name,
                parent_company_slug=b.entity.slug,
                ownership_type=b.entity.ownership_type,
                composite_score=score_res.composite_score,
                confidence=score_res.confidence,
            )
        )
    return results


@router.get("/{slug}", response_model=BrandDetail)
def get_brand_by_slug(slug: str, db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.slug == slug).first()
    if not brand:
        raise HTTPException(status_code=404, detail=f"Brand '{slug}' not found")

    entity = brand.entity
    score_res = score_entity(entity)

    # Convert dimension scores
    dimensions_dict = {}
    for k, d in score_res.dimensions.items():
        dimensions_dict[k] = DimensionScoreSchema(
            key=d.key,
            name=d.name,
            value=d.value,
            confidence=d.confidence,
            status=d.status,
            weight=d.weight,
            explanation=d.explanation,
            evidence=[
                EvidenceSchema(
                    id=ev["id"],
                    dimension=ev["dimension"],
                    fact_text=ev["fact_text"],
                    source_url=ev["source_url"],
                    source_name=ev["source_name"],
                    source_type=ev["source_type"],
                    event_date=ev.get("event_date"),
                    retrieved_at=ev["retrieved_at"],
                    impact=ev["impact"],
                    status=ev["status"],
                )
                for ev in d.evidence
            ],
        )

    # Fetch alternatives
    alternatives = (
        db.query(Alternative)
        .filter(Alternative.from_brand_id == brand.id, Alternative.editor_approved == True)
        .all()
    )
    alt_cards = []
    for alt in alternatives:
        target_brand = alt.to_brand
        target_score = score_entity(target_brand.entity)
        alt_cards.append(
            AlternativeCard(
                id=alt.id,
                brand_name=target_brand.name,
                brand_slug=target_brand.slug,
                parent_name=target_brand.entity.name,
                ownership_type=target_brand.entity.ownership_type,
                composite_score=target_score.composite_score,
                rationale=alt.rationale,
                price_band=alt.price_band,
                where_to_buy=alt.where_to_buy,
                savings_estimate=alt.savings_estimate,
            )
        )

    parent_summary = EntityScoreSummary(
        id=entity.id,
        name=entity.name,
        slug=entity.slug,
        ownership_type=entity.ownership_type,
        hq_city=entity.hq_city,
        hq_state=entity.hq_state,
        locality_tier=entity.locality_tier,
        composite_score=score_res.composite_score,
        confidence=score_res.confidence,
        dimensions=dimensions_dict,
    )

    all_evidence = [
        EvidenceSchema(
            id=ev.id,
            dimension=ev.dimension,
            fact_text=ev.fact_text,
            source_url=ev.source_url,
            source_name=ev.source_name,
            source_type=ev.source_type,
            event_date=ev.event_date,
            retrieved_at=ev.retrieved_at,
            impact=ev.impact,
            status=ev.status,
        )
        for ev in entity.evidence_items
        if ev.status == "published"
    ]

    return BrandDetail(
        id=brand.id,
        name=brand.name,
        slug=brand.slug,
        description=brand.description,
        website=brand.website,
        category_tags=brand.category_tags or [],
        parent_entity=parent_summary,
        scorecard=dimensions_dict,
        composite_score=score_res.composite_score,
        confidence=score_res.confidence,
        evidence=all_evidence,
        alternatives=alt_cards,
    )
