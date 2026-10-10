from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.app.db.session import get_db
from api.app.models.core import HealthcareIntegrity

router = APIRouter(prefix="/v1/healthcare", tags=["Healthcare Integrity & Comparisons"])

WITHHELD_TEXT = "Withheld: no cited source yet"

# A value is published only when it has a cited source: a claim_sources entry with a citation
# and an http(s) url. SEC-backed fields may instead cite the entity's SEC 10-K receipt
# (sec_receipt_details.filing_url). The page template and its JavaScript apply the same rule.
SEC_BACKED_FIELDS = {
    "parent_organization",
    "ownership_type",
    "ownership_tier",
    "shareholder_extraction_pct",
    "exec_comp_pct",
}
# The composite score is the rating; the grade is published only when the score is cited.
RATING_FIELD = "composite_score"
# Swap name is the recommendation; swap slug and type are published only when the swap name is cited.
SWAP_FIELD = "swap_name"


def _is_http_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def cited_source(r: HealthcareIntegrity, field: str) -> Optional[Dict[str, str]]:
    """Return the source that backs a field, or None when the field is unsourced."""
    src = (r.claim_sources or {}).get(field)
    if isinstance(src, dict) and _is_http_url(src.get("url")) and str(src.get("citation", "")).strip():
        return {"url": src["url"], "citation": str(src["citation"])}
    if field in SEC_BACKED_FIELDS:
        sec = r.sec_receipt_details if isinstance(r.sec_receipt_details, dict) else {}
        if _is_http_url(sec.get("filing_url")):
            return {"url": sec["filing_url"], "citation": r.source_citation or "SEC Form 10-K"}
    return None


def _shown(r: HealthcareIntegrity, field: str) -> Any:
    """The field's value when it has a cited source, otherwise None (withheld)."""
    value = getattr(r, field)
    if value is None or cited_source(r, field) is None:
        return None
    return value


def _title(value: Optional[str]) -> Optional[str]:
    return value.replace("_", " ").title() if value else None


def _sort_key(r: HealthcareIntegrity):
    score = _shown(r, RATING_FIELD)
    return (score is None, -(score or 0), r.name or "")


def _matches_query(r: HealthcareIntegrity, q_clean: str) -> bool:
    tokens = [t for t in q_clean.split() if t]
    no_space = q_clean.replace(" ", "")
    haystacks = [(r.name or "").lower(), (_shown(r, "city") or "").lower()]
    for field in ("parent_organization", SWAP_FIELD):
        value = _shown(r, field)
        if value:
            haystacks.append(str(value).lower())
    if any(q_clean in h or no_space in h.replace(" ", "") for h in haystacks):
        return True
    return len(tokens) > 1 and all(any(t in h for h in haystacks) for t in tokens)


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
    limit: int = Query(50, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Query the healthcare integrity database. Unsourced claims are withheld (null) and listed in withheld_claims.
    Filters match cited values only, so a filter never reveals a value that is not published."""
    query = db.query(HealthcareIntegrity)
    if entity_type and entity_type != "all":
        query = query.filter(HealthcareIntegrity.entity_type == entity_type)
    if state and state != "all":
        query = query.filter(HealthcareIntegrity.state == state.upper())

    q_clean = q.strip().lower() if q else ""
    matched = []
    for r in query.all():
        if q_clean and not _matches_query(r, q_clean):
            continue
        if tier is not None and _shown(r, "ownership_tier") != tier:
            continue
        if grade and grade != "all":
            rated_grade = r.grade if _shown(r, RATING_FIELD) is not None else None
            if not (rated_grade or "").startswith(grade):
                continue
        if is_pe_rollup is not None and _shown(r, "is_pe_rollup") != is_pe_rollup:
            continue
        if min_claims_denial is not None:
            rate = _shown(r, "claims_denial_rate_pct")
            if rate is None or rate < min_claims_denial:
                continue
        if min_markup is not None:
            markup = _shown(r, "charge_to_cost_ratio")
            if markup is None or markup < min_markup:
                continue
        matched.append(r)

    matched.sort(key=_sort_key)
    page = matched[offset: offset + limit]

    return {
        "total": len(matched),
        "offset": offset,
        "limit": limit,
        "entities": [serialize_entity(r) for r in page],
    }


@router.get("/compare")
def compare_healthcare_entities(
    slugs: str = Query(..., description="Comma-separated slugs to compare, e.g. 'unitedhealthcare-optum,kaiser-permanente,plum-health-direct-primary-care'"),
    db: Session = Depends(get_db),
):
    """Side-by-side comparison of 2 to 6 healthcare entities across ownership, revenue splits, denial rates, and markups.
    Values without a cited source are null; no ranking is produced unless a rating is cited."""
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

    # Metrics matrix built from the published (cited-only) values
    metrics_comparison = {
        "names": [s["name"] for s in serialized],
        "slugs": [s["slug"] for s in serialized],
        "ownership_tier": [s["ownership_tier"] for s in serialized],
        "ownership_type": [_title(s["ownership_type"]) for s in serialized],
        "composite_score": [s["composite_score"] for s in serialized],
        "grade": [s["grade"] for s in serialized],
        "clinical_care_wages_pct": [s["clinical_care_wages_pct"] for s in serialized],
        "admin_overhead_pct": [s["admin_overhead_pct"] for s in serialized],
        "exec_comp_pct": [s["exec_comp_pct"] for s in serialized],
        "shareholder_extraction_pct": [s["shareholder_extraction_pct"] for s in serialized],
        "medical_loss_ratio_pct": [s["medical_loss_ratio_pct"] for s in serialized],
        "claims_denial_rate_pct": [s["claims_denial_rate_pct"] for s in serialized],
        "charge_to_cost_ratio": [s["charge_to_cost_ratio"] for s in serialized],
        "charity_care_pct": [s["charity_care_pct"] for s in serialized],
        "is_pe_rollup": [s["is_pe_rollup"] for s in serialized],
        "swap_name": [s["swap_name"] for s in serialized],
    }

    # Highest rating among entities that have a cited rating (Shoptegrity opinion)
    rated = [s for s in serialized if s["composite_score"] is not None]
    if rated:
        winner = max(rated, key=lambda s: s["composite_score"])
        highest = {
            "name": winner["name"],
            "slug": winner["slug"],
            "tier": winner["ownership_tier"],
            "score": winner["composite_score"],
            "grade": winner["grade"],
            "rationale": (
                f"{winner['name']} has the highest Shoptegrity rating ({winner['composite_score']}/100, "
                f"Shoptegrity opinion) among the entities compared that have a cited rating."
            ),
        }
    else:
        highest = {
            "name": None,
            "slug": None,
            "tier": None,
            "score": None,
            "grade": None,
            "rationale": WITHHELD_TEXT,
        }

    return {
        "compared_count": len(ordered_records),
        "entities": serialized,
        "metrics_matrix": metrics_comparison,
        "highest_integrity_entity": highest,
    }


@router.get("/stats")
def get_healthcare_stats(db: Session = Depends(get_db)):
    """Summary statistics across the healthcare database. Entity counts are dataset counts;
    tier, PE and average figures use cited values only (averages are null when nothing is cited)."""
    rows = db.query(HealthcareIntegrity).all()
    total = len(rows)

    type_counts: Dict[str, int] = {}
    tier_counts: Dict[int, int] = {}
    pe_rollups = 0
    pe_known = 0
    for r in rows:
        type_counts[r.entity_type] = type_counts.get(r.entity_type, 0) + 1
        tier = _shown(r, "ownership_tier")
        if tier is not None:
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        if _shown(r, "is_pe_rollup") is not None:
            pe_known += 1
        if _shown(r, "is_pe_rollup") is True:
            pe_rollups += 1

    def _avg(values):
        vals = [v for v in values if v is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    return {
        "total_entities": total,
        "by_entity_type": type_counts,
        "by_ownership_tier": tier_counts,
        # Null until at least one record has a cited PE determination; zero would read as "none found"
        "pe_rollups_count": pe_rollups if pe_known else None,
        "pe_rollups_pct": round(pe_rollups / pe_known * 100, 1) if pe_known else None,
        "averages": {
            "composite_score": _avg(_shown(r, RATING_FIELD) for r in rows),
            "clinical_care_wages_pct": _avg(_shown(r, "clinical_care_wages_pct") for r in rows),
            "shareholder_extraction_pct": _avg(_shown(r, "shareholder_extraction_pct") for r in rows),
            "insurers_claims_denial_pct": _avg(
                _shown(r, "claims_denial_rate_pct") for r in rows if r.entity_type == "health_insurance"
            ),
            "hospitals_charge_to_cost_markup": _avg(
                _shown(r, "charge_to_cost_ratio") for r in rows if r.entity_type == "hospital_chain"
            ),
        },
    }


@router.get("/{slug}")
def get_healthcare_entity_detail(slug: str, db: Session = Depends(get_db)):
    """Retrieve detailed scorecard, financial splits, and recommended swaps for an individual healthcare entity."""
    record = db.query(HealthcareIntegrity).filter(HealthcareIntegrity.slug == slug).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Healthcare entity '{slug}' not found")
    return serialize_entity(record)


def serialize_entity(r: HealthcareIntegrity) -> Dict[str, Any]:
    """Public view of one entity. Identity fields are always shown; every claim without a cited
    source is None (or [] for lists) and is named in withheld_claims."""
    rated = _shown(r, RATING_FIELD) is not None
    swap_cited = _shown(r, SWAP_FIELD) is not None
    return {
        "id": r.id,
        "name": r.name,
        "slug": r.slug,
        "entity_type": r.entity_type,
        "sub_category": r.sub_category,
        "parent_organization": _shown(r, "parent_organization"),
        "ownership_type": _shown(r, "ownership_type"),
        "ownership_tier": _shown(r, "ownership_tier"),
        "composite_score": _shown(r, RATING_FIELD),
        "grade": r.grade if rated else None,
        "clinical_care_wages_pct": _shown(r, "clinical_care_wages_pct"),
        "admin_overhead_pct": _shown(r, "admin_overhead_pct"),
        "exec_comp_pct": _shown(r, "exec_comp_pct"),
        "shareholder_extraction_pct": _shown(r, "shareholder_extraction_pct"),
        "supplies_operations_pct": _shown(r, "supplies_operations_pct"),
        "medical_loss_ratio_pct": _shown(r, "medical_loss_ratio_pct"),
        "claims_denial_rate_pct": _shown(r, "claims_denial_rate_pct"),
        "charge_to_cost_ratio": _shown(r, "charge_to_cost_ratio"),
        "charity_care_pct": _shown(r, "charity_care_pct"),
        "is_pe_rollup": _shown(r, "is_pe_rollup"),
        "pe_firm_name": _shown(r, "pe_firm_name"),
        "regulatory_citations": list(r.regulatory_citations or []) if cited_source(r, "regulatory_citations") else [],
        "swap_name": _shown(r, SWAP_FIELD),
        "swap_slug": r.swap_slug if swap_cited else None,
        "swap_type": r.swap_type if swap_cited else None,
        "swap_rationale": _shown(r, "swap_rationale"),
        "location_scope": r.location_scope,
        "city": _shown(r, "city"),
        "state": _shown(r, "state"),
        "data_provenance": r.data_provenance,
        "source_citation": r.source_citation,
        "filing_url": r.filing_url,
        "summary_notes": _shown(r, "summary_notes"),
        "sec_receipt_details": r.sec_receipt_details,
        "claim_sources": r.claim_sources or {},
        "withheld_claims": r.withheld_claims or [],
        "split_basis": r.split_basis or {},
        "rating_type": r.rating_type,
    }
