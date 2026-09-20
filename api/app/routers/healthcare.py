from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from api.app.db.session import get_db
from api.app.models.core import HealthcareIntegrity

router = APIRouter(prefix="/v1/healthcare", tags=["Healthcare Integrity & Comparisons"])


@router.get("/database")
def get_healthcare_database(
    q: Optional[str] = Query(None, description="Search by entity name, parent organization, or city"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type: health_insurance, hospital_chain, corporate_clinic, local_clinic"),
    tier: Optional[int] = Query(None, ge=1, le=6, description="Filter by ownership tier (1-6)"),
    grade: Optional[str] = Query(None, description="Filter by grade: A+, A, B, C, D, F"),
    is_pe_rollup: Optional[bool] = Query(None, description="Filter by PE rollup flag"),
    state: Optional[str] = Query(None, description="Filter by two-letter state code"),
    min_claims_denial: Optional[float] = Query(None, description="Filter entities with claims denial rate >= pct"),
    min_markup: Optional[float] = Query(None, description="Filter entities with charge-to-cost markup >= x"),
    limit: int = Query(50, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Query the 2,000 healthcare entities integrity database with full financial splits and clinical metrics."""
    query = db.query(HealthcareIntegrity)

    if q:
        search_pat = f"%{q.lower()}%"
        query = query.filter(
            or_(
                HealthcareIntegrity.name.ilike(search_pat),
                HealthcareIntegrity.parent_organization.ilike(search_pat),
                HealthcareIntegrity.city.ilike(search_pat),
                HealthcareIntegrity.swap_name.ilike(search_pat),
            )
        )
    if entity_type and entity_type != "all":
        query = query.filter(HealthcareIntegrity.entity_type == entity_type)
    if tier is not None:
        query = query.filter(HealthcareIntegrity.ownership_tier == tier)
    if grade and grade != "all":
        query = query.filter(HealthcareIntegrity.grade.startswith(grade))
    if is_pe_rollup is not None:
        query = query.filter(HealthcareIntegrity.is_pe_rollup == is_pe_rollup)
    if state and state != "all":
        query = query.filter(HealthcareIntegrity.state == state.upper())
    if min_claims_denial is not None:
        query = query.filter(HealthcareIntegrity.claims_denial_rate_pct >= min_claims_denial)
    if min_markup is not None:
        query = query.filter(HealthcareIntegrity.charge_to_cost_ratio >= min_markup)

    total_matches = query.count()
    records = query.order_by(HealthcareIntegrity.composite_score.desc()).offset(offset).limit(limit).all()

    return {
        "total": total_matches,
        "offset": offset,
        "limit": limit,
        "entities": [serialize_entity(r) for r in records],
    }


@router.get("/compare")
def compare_healthcare_entities(
    slugs: str = Query(..., description="Comma-separated slugs to compare, e.g. 'unitedhealthcare-optum,kaiser-permanente,plum-health-direct-primary-care'"),
    db: Session = Depends(get_db),
):
    """Side-by-side comparison of 2 to 6 healthcare entities across ownership, revenue splits, denial rates, and markups."""
    slug_list = [s.strip().lower() for s in slugs.split(",") if s.strip()]
    if not slug_list:
        raise HTTPException(status_code=400, detail="Must provide at least one slug to compare")
    if len(slug_list) > 6:
        raise HTTPException(status_code=400, detail="Maximum 6 entities can be compared simultaneously")

    records = db.query(HealthcareIntegrity).filter(HealthcareIntegrity.slug.in_(slug_list)).all()
    records_by_slug = {r.slug: r for r in records}

    # Maintain original request order
    ordered_records = [records_by_slug[s] for s in slug_list if s in records_by_slug]
    if not ordered_records:
        raise HTTPException(status_code=404, detail="None of the specified slugs were found")

    serialized = [serialize_entity(r) for r in ordered_records]

    # Metrics Matrix for easy client rendering
    metrics_comparison = {
        "names": [r.name for r in ordered_records],
        "slugs": [r.slug for r in ordered_records],
        "ownership_tier": [r.ownership_tier for r in ordered_records],
        "ownership_type": [r.ownership_type.replace('_', ' ').title() for r in ordered_records],
        "composite_score": [r.composite_score for r in ordered_records],
        "grade": [r.grade for r in ordered_records],
        "clinical_care_wages_pct": [r.clinical_care_wages_pct for r in ordered_records],
        "admin_overhead_pct": [r.admin_overhead_pct for r in ordered_records],
        "exec_comp_pct": [r.exec_comp_pct for r in ordered_records],
        "shareholder_extraction_pct": [r.shareholder_extraction_pct for r in ordered_records],
        "medical_loss_ratio_pct": [r.medical_loss_ratio_pct for r in ordered_records],
        "claims_denial_rate_pct": [r.claims_denial_rate_pct for r in ordered_records],
        "charge_to_cost_ratio": [r.charge_to_cost_ratio for r in ordered_records],
        "charity_care_pct": [r.charity_care_pct for r in ordered_records],
        "is_pe_rollup": [r.is_pe_rollup for r in ordered_records],
        "swap_name": [r.swap_name for r in ordered_records],
    }

    # Best-in-comparison integrity winner
    winner = max(ordered_records, key=lambda x: x.composite_score)

    return {
        "compared_count": len(ordered_records),
        "entities": serialized,
        "metrics_matrix": metrics_comparison,
        "highest_integrity_entity": {
            "name": winner.name,
            "slug": winner.slug,
            "tier": winner.ownership_tier,
            "score": winner.composite_score,
            "grade": winner.grade,
            "rationale": f"{winner.name} retains {winner.clinical_care_wages_pct}% of revenue for frontline clinical care with 0% Wall Street shareholder extraction."
        }
    }


@router.get("/stats")
def get_healthcare_stats(db: Session = Depends(get_db)):
    """Summary statistics across the 2,000 healthcare entities database."""
    total = db.query(HealthcareIntegrity).count()

    type_counts = dict(
        db.query(HealthcareIntegrity.entity_type, func.count(HealthcareIntegrity.id))
        .group_by(HealthcareIntegrity.entity_type)
        .all()
    )

    tier_counts = dict(
        db.query(HealthcareIntegrity.ownership_tier, func.count(HealthcareIntegrity.id))
        .group_by(HealthcareIntegrity.ownership_tier)
        .all()
    )

    pe_rollups = db.query(HealthcareIntegrity).filter(HealthcareIntegrity.is_pe_rollup == True).count()

    # Averages
    avg_score = db.query(func.avg(HealthcareIntegrity.composite_score)).scalar() or 0.0
    avg_care = db.query(func.avg(HealthcareIntegrity.clinical_care_wages_pct)).scalar() or 0.0
    avg_extraction = db.query(func.avg(HealthcareIntegrity.shareholder_extraction_pct)).scalar() or 0.0
    avg_denial_insurers = (
        db.query(func.avg(HealthcareIntegrity.claims_denial_rate_pct))
        .filter(HealthcareIntegrity.entity_type == "health_insurance")
        .scalar() or 0.0
    )
    avg_markup_hospitals = (
        db.query(func.avg(HealthcareIntegrity.charge_to_cost_ratio))
        .filter(HealthcareIntegrity.entity_type == "hospital_chain")
        .scalar() or 0.0
    )

    return {
        "total_entities": total,
        "by_entity_type": type_counts,
        "by_ownership_tier": tier_counts,
        "pe_rollups_count": pe_rollups,
        "pe_rollups_pct": round((pe_rollups / total * 100) if total > 0 else 0, 1),
        "averages": {
            "composite_score": round(avg_score, 1),
            "clinical_care_wages_pct": round(avg_care, 1),
            "shareholder_extraction_pct": round(avg_extraction, 1),
            "insurers_claims_denial_pct": round(avg_denial_insurers, 1),
            "hospitals_charge_to_cost_markup": round(avg_markup_hospitals, 1),
        }
    }


@router.get("/{slug}")
def get_healthcare_entity_detail(slug: str, db: Session = Depends(get_db)):
    """Retrieve detailed scorecard, financial splits, and recommended swaps for an individual healthcare entity."""
    record = db.query(HealthcareIntegrity).filter(HealthcareIntegrity.slug == slug).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Healthcare entity '{slug}' not found")
    return serialize_entity(record)


def serialize_entity(r: HealthcareIntegrity) -> Dict[str, Any]:
    return {
        "id": r.id,
        "name": r.name,
        "slug": r.slug,
        "entity_type": r.entity_type,
        "sub_category": r.sub_category,
        "parent_organization": r.parent_organization,
        "ownership_type": r.ownership_type,
        "ownership_tier": r.ownership_tier,
        "composite_score": r.composite_score,
        "grade": r.grade,
        "clinical_care_wages_pct": r.clinical_care_wages_pct,
        "admin_overhead_pct": r.admin_overhead_pct,
        "exec_comp_pct": r.exec_comp_pct,
        "shareholder_extraction_pct": r.shareholder_extraction_pct,
        "supplies_operations_pct": r.supplies_operations_pct,
        "medical_loss_ratio_pct": r.medical_loss_ratio_pct,
        "claims_denial_rate_pct": r.claims_denial_rate_pct,
        "charge_to_cost_ratio": r.charge_to_cost_ratio,
        "charity_care_pct": r.charity_care_pct,
        "is_pe_rollup": r.is_pe_rollup,
        "pe_firm_name": r.pe_firm_name,
        "regulatory_citations": r.regulatory_citations or [],
        "swap_name": r.swap_name,
        "swap_slug": r.swap_slug,
        "swap_type": r.swap_type,
        "swap_rationale": r.swap_rationale,
        "location_scope": r.location_scope,
        "city": r.city,
        "state": r.state,
        "data_provenance": r.data_provenance,
        "source_citation": r.source_citation,
        "filing_url": r.filing_url,
        "summary_notes": r.summary_notes,
    }
