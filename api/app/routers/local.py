from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_

from api.app.db.session import get_db, haversine_distance_km
from api.app.models.core import Place, Entity
from api.app.schemas.domain import PlaceSummary

router = APIRouter(prefix="/v1/local", tags=["Local Services & Places"])


class MatchRequest(BaseModel):
    name: str
    address: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class MatchResponse(BaseModel):
    matched: bool
    place: Optional[PlaceSummary] = None
    warning_flag: Optional[str] = None
    ownership_explanation: str


@router.get("/places", response_model=List[PlaceSummary])
def list_local_places(
    lat: Optional[float] = Query(None, description="User latitude"),
    lon: Optional[float] = Query(None, description="User longitude"),
    radius_km: float = Query(50.0, description="Search radius in kilometers"),
    category: Optional[str] = Query(None, description="Category filter (farmers_market, food_coop, credit_union, plumber, etc.)"),
    max_tier: Optional[int] = Query(None, description="Maximum ownership tier (1-6, lower is more local)"),
    flag: Optional[str] = Query(None, description="Flag filter (coop, rollup_disguised, snap_ebt, organic)"),
    db: Session = Depends(get_db),
):
    """Proximity search for local businesses, co-ops, markets, and services."""
    query = db.query(Place)
    if category:
        query = query.filter(Place.category == category)
    if max_tier is not None:
        query = query.filter(Place.ownership_tier <= max_tier)

    all_places = query.all()
    results = []

    for p in all_places:
        if flag and (not p.flags or flag not in p.flags):
            continue

        dist = None
        if lat is not None and lon is not None:
            dist = haversine_distance_km(lat, lon, p.lat, p.lon)
            if dist > radius_km:
                continue

        results.append(
            PlaceSummary(
                id=p.id,
                name=p.name,
                slug=p.slug,
                category=p.category,
                address=p.address,
                city=p.city,
                state=p.state,
                postal_code=p.postal_code,
                lat=p.lat,
                lon=p.lon,
                phone=p.phone,
                website=p.website,
                ownership_tier=p.ownership_tier,
                flags=p.flags or [],
                verified_locally=p.verified_locally,
                verified_how=p.verified_how,
                hours=p.hours,
                season=p.season,
                distance_km=dist,
            )
        )

    if lat is not None and lon is not None:
        results.sort(key=lambda x: (x.distance_km if x.distance_km is not None else 999999))

    return results


@router.post("/match", response_model=MatchResponse)
def match_business_place(req: MatchRequest, db: Session = Depends(get_db)):
    """Matches a business (e.g. from Google Maps overlay or search) and evaluates ownership integrity."""
    norm_name = req.name.strip().lower()

    # Search for matching place
    candidates = db.query(Place).filter(Place.name.ilike(f"%{norm_name}%")).all()

    if not candidates:
        return MatchResponse(
            matched=False,
            place=None,
            warning_flag=None,
            ownership_explanation="No verified ownership record found in the database. Classified as Tier 0 (Ownership Unverified).",
        )

    # Pick best candidate based on distance if coords provided
    best = candidates[0]
    if req.lat is not None and req.lon is not None and len(candidates) > 1:
        candidates.sort(key=lambda p: haversine_distance_km(req.lat, req.lon, p.lat, p.lon))
        best = candidates[0]

    dist = haversine_distance_km(req.lat, req.lon, best.lat, best.lon) if (req.lat and req.lon) else None

    summary = PlaceSummary(
        id=best.id,
        name=best.name,
        slug=best.slug,
        category=best.category,
        address=best.address,
        city=best.city,
        state=best.state,
        postal_code=best.postal_code,
        lat=best.lat,
        lon=best.lon,
        phone=best.phone,
        website=best.website,
        ownership_tier=best.ownership_tier,
        flags=best.flags or [],
        verified_locally=best.verified_locally,
        verified_how=best.verified_how,
        hours=best.hours,
        season=best.season,
        distance_km=dist,
    )

    warning = None
    explanation = f"Tier {best.ownership_tier}: "
    if "rollup_disguised" in (best.flags or []):
        warning = "DISGUISED_ROLLUP"
        explanation += f"CAUTION: Operating under a legacy local name, but acquired by a private equity platform ({best.entity.name if best.entity else 'Private Equity'})."
    elif best.ownership_tier == 1:
        explanation += "Verified owner-operated local business. Single location, owner resides in the metro."
    elif best.ownership_tier == 2:
        explanation += "Verified local multi-location business owned within the metro."
    elif best.ownership_tier == 3:
        explanation += "Locally owned franchise location (franchise royalties leave the metro)."
    elif "coop" in (best.flags or []):
        explanation += "Democratically governed cooperative owned by workers or community members."
    else:
        explanation += f"Ownership tier {best.ownership_tier}."

    return MatchResponse(
        matched=True,
        place=summary,
        warning_flag=warning,
        ownership_explanation=explanation,
    )
