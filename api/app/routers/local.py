import re
from typing import Any, Dict, List, Optional, Tuple
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.app.db.session import get_db, haversine_distance_km
from api.app.models.core import Evidence, Place
from api.app.schemas.domain import PlaceSummary

router = APIRouter(prefix="/v1/local", tags=["Local Services & Places"])

WITHHELD = "Withheld: no cited source yet"
DEMO_FLAG = "demo_listing"
ROLLUP_FLAG = "rollup_disguised"
OWNERSHIP_FLAGS = (ROLLUP_FLAG, "coop")

MIN_QUERY_CHARS = 3
# Jaccard overlap of name tokens. Without coordinates the name must nearly match.
# With coordinates a looser name match is accepted only inside the distance threshold.
NAME_MATCH_MIN_SCORE = 0.55
NAME_MATCH_MIN_SCORE_WITH_COORDS = 0.5
MATCH_MAX_DISTANCE_KM = 2.0


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


def _tokens(text: Optional[str]) -> List[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _token_score(query_tokens: List[str], name_tokens: List[str]) -> float:
    """Jaccard overlap of token sets. One shared word does not match a longer name."""
    q, n = set(query_tokens), set(name_tokens)
    if not q or not n:
        return 0.0
    return len(q & n) / len(q | n)


def _is_demo(place: Place) -> bool:
    return DEMO_FLAG in (place.flags or [])


def _cited_ownership(place: Place) -> Optional[Evidence]:
    """First published ownership record with a source URL on the place's entity, if any."""
    entity = place.entity
    if entity is None:
        return None
    for ev in entity.evidence_items:
        if ev.dimension == "ownership" and ev.status == "published" and (ev.source_url or "").strip():
            return ev
    return None


def _public_fields(place: Place) -> Dict[str, Any]:
    """Ownership, flag and verification fields the public API may show.

    Ownership tiers, ownership flags and verification statements are returned only
    when the place's entity has a published ownership record with a source URL.
    Otherwise they are withheld.
    """
    cited = _cited_ownership(place)
    if cited is not None:
        return {
            "cited": cited,
            "ownership_tier": place.ownership_tier or 0,
            "flags": list(place.flags or []),
            "verified_locally": bool(place.verified_locally),
            "verified_how": place.verified_how or "Unverified",
        }
    return {
        "cited": None,
        "ownership_tier": 0,
        "flags": [f for f in (place.flags or []) if f not in OWNERSHIP_FLAGS],
        "verified_locally": False,
        "verified_how": "Unverified",
    }


def _summary(place: Place, fields: Dict[str, Any], dist: Optional[float]) -> PlaceSummary:
    return PlaceSummary(
        id=place.id,
        name=place.name,
        slug=place.slug,
        category=place.category,
        address=place.address,
        city=place.city,
        state=place.state,
        postal_code=place.postal_code,
        lat=place.lat,
        lon=place.lon,
        phone=place.phone,
        website=place.website,
        ownership_tier=fields["ownership_tier"],
        flags=fields["flags"],
        verified_locally=fields["verified_locally"],
        verified_how=fields["verified_how"],
        hours=place.hours,
        season=place.season,
        distance_km=dist,
    )


def _find_best_place(
    places: List[Place], name: str, lat: Optional[float], lon: Optional[float]
) -> Optional[Tuple[Place, Optional[float]]]:
    """Best confident match as (place, distance_km), or None. Demo listings are never matched."""
    query = (name or "").strip()
    query_tokens = _tokens(query)
    if len(query) < MIN_QUERY_CHARS or not query_tokens:
        return None

    has_coords = lat is not None and lon is not None
    min_score = NAME_MATCH_MIN_SCORE_WITH_COORDS if has_coords else NAME_MATCH_MIN_SCORE

    best: Optional[Tuple[Place, Optional[float]]] = None
    best_key: Optional[Tuple[float, float]] = None
    for place in places:
        if _is_demo(place):
            continue
        score = _token_score(query_tokens, _tokens(place.name))
        if score < min_score:
            continue
        dist: Optional[float] = None
        if has_coords:
            dist = haversine_distance_km(lat, lon, place.lat, place.lon)
            if dist > MATCH_MAX_DISTANCE_KM:
                continue
        key = (-score, dist if dist is not None else 0.0)
        if best_key is None or key < best_key:
            best, best_key = (place, dist), key
    return best


@router.get("/places", response_model=List[PlaceSummary])
def list_local_places(
    lat: Optional[float] = Query(None, description="User latitude"),
    lon: Optional[float] = Query(None, description="User longitude"),
    radius_km: float = Query(50.0, description="Search radius in kilometers"),
    category: Optional[str] = Query(None, description="Category filter (farmers_market, food_coop, credit_union, plumber, etc.)"),
    max_tier: Optional[int] = Query(None, description="Maximum cited ownership tier (1-6, lower is more local). Places without a cited tier are excluded."),
    flag: Optional[str] = Query(None, description="Flag filter (coop, rollup_disguised, snap_ebt, organic)"),
    db: Session = Depends(get_db),
):
    """Proximity search for local businesses, co-ops, markets, and services. Demo listings are never returned."""
    query = db.query(Place)
    if category:
        query = query.filter(Place.category == category)

    results = []
    for p in query.all():
        if _is_demo(p):
            continue

        fields = _public_fields(p)
        if max_tier is not None and not (1 <= fields["ownership_tier"] <= max_tier):
            continue
        if flag and flag not in fields["flags"]:
            continue

        dist = None
        if lat is not None and lon is not None:
            dist = haversine_distance_km(lat, lon, p.lat, p.lon)
            if dist > radius_km:
                continue

        results.append(_summary(p, fields, dist))

    if lat is not None and lon is not None:
        results.sort(key=lambda x: (x.distance_km if x.distance_km is not None else 999999))

    return results


@router.post("/match", response_model=MatchResponse)
def match_business_place(req: MatchRequest, db: Session = Depends(get_db)):
    """Matches a business name against the directory and reports ownership only where a cited record exists.

    Names under 3 characters are refused. A match needs token overlap, and when coordinates are
    given, a place within 2 km. Ownership caution is returned only with a published, cited ownership record.
    """
    query = (req.name or "").strip()
    if len(query) < MIN_QUERY_CHARS:
        return MatchResponse(
            matched=False,
            place=None,
            warning_flag=None,
            ownership_explanation=f"Enter at least {MIN_QUERY_CHARS} characters of the business name.",
        )

    found = _find_best_place(db.query(Place).all(), query, req.lat, req.lon)
    if found is None:
        return MatchResponse(
            matched=False,
            place=None,
            warning_flag=None,
            ownership_explanation=f"No match in the directory. Ownership: {WITHHELD}.",
        )

    best, dist = found
    fields = _public_fields(best)
    cited = fields["cited"]
    summary = _summary(best, fields, dist)

    warning = None
    if cited is None:
        explanation = f"Ownership: {WITHHELD}."
    elif ROLLUP_FLAG in (best.flags or []):
        warning = "DISGUISED_ROLLUP"
        explanation = (
            "Caution: a cited ownership record is on file for this business and carries a rollup flag. "
            f"Source: {cited.source_name} ({cited.source_url})."
        )
    elif fields["ownership_tier"]:
        explanation = (
            f"Shoptegrity opinion: ownership tier {fields['ownership_tier']}. "
            f"Cited ownership record: {cited.source_name} ({cited.source_url})."
        )
    else:
        explanation = (
            f"Cited ownership record: {cited.source_name} ({cited.source_url}). Ownership tier not assigned."
        )

    return MatchResponse(
        matched=True,
        place=summary,
        warning_flag=warning,
        ownership_explanation=explanation,
    )
