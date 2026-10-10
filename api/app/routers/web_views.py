from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, Request, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_

from api.app.db.session import get_db
from api.app.models.core import Brand, Entity, SpendCategory, Alternative, Place, Maker, FlowProfile, HealthcareIntegrity
from api.app.routers.food_chain import (
    SOURCING_LADDER,
    fetch_food_dollar_splits,
    FARMLAND_OWNERSHIP_DATA,
    FARM_BUDGET_COMPARISONS,
)
from api.app.routers.swaps import get_swap_guide_detail
from api.app.services.geo_flow_service import SCENARIOS_META, trace_dollar_flow
from api.app.services.scoring_service import score_entity, get_cached_rubric
from api.app.services.citation import cited_ownership_name, cited_ownership_type, has_cited_ownership

templates_dir = Path(__file__).parent.parent.parent.parent / "web" / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

router = APIRouter(tags=["Web Views"])


@router.get("/", response_class=HTMLResponse)
def home_view(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"active_page": "home"},
    )


@router.get("/brands", response_class=HTMLResponse)
def brands_view(request: Request, q: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(Brand).join(Entity, Brand.entity_id == Entity.id)
    if q:
        search_pattern = f"%{q.lower()}%"
        query = query.filter(
            or_(
                Brand.name.ilike(search_pattern),
                Entity.name.ilike(search_pattern),
            )
        )
    brands = query.all()
    brand_summaries = []
    for b in brands:
        score_res = score_entity(b.entity)
        owner_type = cited_ownership_type(b.entity)
        brand_summaries.append({
            "id": b.id,
            "name": b.name,
            "slug": b.slug,
            "description": None,  # withheld: no citation field exists for descriptions
            "parent_company_name": cited_ownership_name(b.entity),
            "ownership_type": owner_type.replace('_', ' ').title() if owner_type else None,
            "composite_score": score_res.composite_score,
            "confidence": score_res.confidence,
        })

    return templates.TemplateResponse(
        request=request,
        name="brands.html",
        context={
            "active_page": "brands",
            "brands": brand_summaries,
            "search_query": q,
        },
    )


@router.get("/brands/{slug}", response_class=HTMLResponse)
def brand_detail_view(request: Request, slug: str, db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.slug == slug).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    entity = brand.entity
    score_res = score_entity(entity)

    dimensions_dict = {}
    for k, d in score_res.dimensions.items():
        dimensions_dict[k] = {
            "key": d.key,
            "name": d.name,
            "value": d.value,
            "confidence": d.confidence,
            "status": d.status,
            "explanation": d.explanation,
        }

    alts = (
        db.query(Alternative)
        .filter(Alternative.from_brand_id == brand.id, Alternative.editor_approved == True)
        .all()
    )
    alt_cards = []
    for alt in alts:
        target_score = score_entity(alt.to_brand.entity)
        alt_cards.append({
            "id": alt.id,
            "brand_name": alt.to_brand.name,
            "brand_slug": alt.to_brand.slug,
            "parent_name": cited_ownership_name(alt.to_brand.entity),
            "ownership_type": cited_ownership_type(alt.to_brand.entity),
            "composite_score": target_score.composite_score,
            "rationale": None,  # withheld until cited (R1)
            "price_band": None,  # withheld until cited (R1)
            "where_to_buy": None,  # withheld until cited (R1)
            "savings_estimate": None,  # withheld until cited (R1)
            "swap_tier": getattr(alt, "swap_tier", "best"),
            "similarity_notes": getattr(alt, "similarity_notes", None),
        })

    # Evidence attached to the parent entity is shown only once the brand-to-parent link is cited
    evidence_list = [
        {
            "dimension": ev.dimension,
            "fact_text": ev.fact_text,
            "source_url": ev.source_url,
            "source_name": ev.source_name,
        }
        for ev in entity.evidence_items
        if ev.status == "published" and has_cited_ownership(entity)
    ]

    owner_type = cited_ownership_type(entity)
    brand_data = {
        "id": brand.id,
        "name": brand.name,
        "slug": brand.slug,
        "description": None,  # withheld: no citation field exists for descriptions
        "website": brand.website,
        "parent_entity": {
            "name": cited_ownership_name(entity),
            "ownership_type": owner_type.replace('_', ' ').title() if owner_type else None,
        },
        "composite_score": score_res.composite_score,
        "confidence": score_res.confidence,
        "scorecard": dimensions_dict,
        "alternatives": alt_cards,
        "evidence": evidence_list,
    }

    return templates.TemplateResponse(
        request=request,
        name="brand_detail.html",
        context={
            "active_page": "brands",
            "brand": brand_data,
        },
    )


@router.get("/food", response_class=HTMLResponse)
def food_view(request: Request, db: Session = Depends(get_db)):
    splits = fetch_food_dollar_splits()
    makers = db.query(Maker).all()
    local_places = db.query(Place).filter(Place.category.in_(["food_coop", "farmers_market", "csa"])).all()

    return templates.TemplateResponse(
        request=request,
        name="food.html",
        context={
            "active_page": "food",
            "sourcing_ladder": SOURCING_LADDER,
            "dollar_splits": splits,
            "makers": makers,
            "local_food_places": local_places,
            "farmland_ownership": FARMLAND_OWNERSHIP_DATA,
            "farm_budgets": FARM_BUDGET_COMPARISONS,
        },
    )


@router.get("/local", response_class=HTMLResponse)
def local_view(request: Request, db: Session = Depends(get_db)):
    # Demo listings are never shown publicly
    places = [p for p in db.query(Place).all() if "demo_listing" not in (p.flags or [])]
    return templates.TemplateResponse(
        request=request,
        name="local.html",
        context={
            "active_page": "local",
            "places": places,
        },
    )


@router.get("/swaps", response_class=HTMLResponse)
def swaps_view(request: Request, db: Session = Depends(get_db)):
    categories = db.query(SpendCategory).all()
    guides = [get_swap_guide_detail(c.slug, db) for c in categories]

    return templates.TemplateResponse(
        request=request,
        name="swaps.html",
        context={
            "active_page": "swaps",
            "swap_guides": guides,
        },
    )

@router.get("/flows", response_class=HTMLResponse)
def flows_view(
    request: Request,
    zip: str = Query("55401"),
    scenario: str = Query("grocery_produce"),
    spend: float = Query(100.0),
    db: Session = Depends(get_db),
):
    clean_zip = zip.strip()[:5] if zip else "55401"
    if len(clean_zip) < 5 or not clean_zip.isdigit():
        clean_zip = "55401"
    valid_scenario = scenario if scenario in [s.id for s in SCENARIOS_META] else "grocery_produce"
    valid_spend = spend if spend > 0 else 100.0

    trace_data = trace_dollar_flow(origin_zip=clean_zip, scenario_id=valid_scenario, spend_amount=valid_spend)

    return templates.TemplateResponse(
        request=request,
        name="flows.html",
        context={
            "active_page": "flows",
            "trace": trace_data,
            "scenarios": SCENARIOS_META,
            "selected_scenario": valid_scenario,
            "origin_zip": clean_zip,
            "spend_amount": valid_spend,
        },
    )



@router.get("/methodology", response_class=HTMLResponse)
def methodology_view(request: Request):
    rubric = get_cached_rubric()
    data_sources = [
        {"name": "SEC EDGAR", "type": "Public Filings", "metrics": ["Pay Ratio", "Dividends", "Buybacks"], "url": "https://www.sec.gov/edgar"},
        {"name": "USDA ERS Food Dollar", "type": "Federal Agency", "metrics": ["Farm share", "Supply chain margins"], "url": "https://www.ers.usda.gov"},
        {"name": "OSHA Enforcement", "type": "Workplace Safety", "metrics": ["Violations", "Severe injuries"], "url": "https://www.osha.gov"},
        {"name": "EPA ECHO", "type": "Environmental History", "metrics": ["Water and air compliance", "Toxic release"], "url": "https://echo.epa.gov"},
        {"name": "NCUA Credit Union Directory", "type": "Federal Regulator", "metrics": ["Member assets", "Cooperative charters"], "url": "https://www.ncua.gov"},
    ]

    return templates.TemplateResponse(
        request=request,
        name="methodology.html",
        context={
            "active_page": "methodology",
            "rubric": rubric,
            "data_sources": data_sources,
        },
    )


@router.get("/sell-direct", response_class=HTMLResponse)
def sell_direct_view(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="sell_direct.html",
        context={"active_page": "sell-direct"},
    )


@router.get("/disclosures", response_class=HTMLResponse)
def disclosures_view(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="disclosures.html",
        context={"active_page": "disclosures"},
    )


@router.get("/corrections", response_class=HTMLResponse)
def corrections_view(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="corrections.html",
        context={"active_page": "corrections"},
    )


@router.get("/parents", response_class=HTMLResponse)
def parents_view(
    request: Request,
    q: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
):
    from api.app.services.parent_lookup_service import parent_service

    # The subterfuge filter was withdrawn: parent-company flags are not published until cited.
    feed_data = parent_service.get_feed(
        q=q,
        category=category,
        limit=60,
    )
    stats = parent_service.get_stats()

    return templates.TemplateResponse(
        request=request,
        name="parents.html",
        context={
            "active_page": "parents",
            "feed_results": feed_data["results"],
            "total_count": feed_data["total"],
            "stats": stats,
            "search_query": q,
            "selected_category": category,
            "subterfuge_only": False,
        },
    )


@router.get("/healthcare", response_class=HTMLResponse)
def healthcare_view(
    request: Request,
    q: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(HealthcareIntegrity)
    if q:
        from sqlalchemy import and_
        q_clean = q.strip().lower()
        search_pat = f"%{q_clean}%"
        search_no_space = f"%{q_clean.replace(' ', '')}%"
        tokens = [f"%{t}%" for t in q_clean.split() if t]
        # Search names and cities only. Parent organizations are withheld until cited, so they are not searchable.
        conditions = [
            HealthcareIntegrity.name.ilike(search_pat),
            HealthcareIntegrity.name.ilike(search_no_space),
            HealthcareIntegrity.city.ilike(search_pat),
        ]
        if len(tokens) > 1:
            conditions.append(and_(*[HealthcareIntegrity.name.ilike(t) for t in tokens]))
        query = query.filter(or_(*conditions))
    if sector and sector != "all":
        query = query.filter(HealthcareIntegrity.entity_type == sector)

    # Ratings are withheld until their inputs are cited, so list alphabetically rather than by score
    initial_entities = query.order_by(HealthcareIntegrity.name).limit(24).all()
    total_count = query.count()

    return templates.TemplateResponse(
        request=request,
        name="healthcare.html",
        context={
            "active_page": "healthcare",
            "initial_entities": initial_entities,
            "total_count": total_count,
            "search_query": q,
            "selected_sector": sector,
        },
    )


@router.get("/housing", response_class=HTMLResponse)
def housing_view(request: Request):
    """Renders the comprehensive Housing & Rental Integrity Guide."""
    from api.app.routers.housing import (
        DEMOGRAPHIC_DATA,
        RENT_DOLLAR_SPLITS,
        OWNERSHIP_LADDER,
        MEGA_LANDLORDS,
        HOUSING_SWAPS,
    )

    return templates.TemplateResponse(
        request=request,
        name="housing.html",
        context={
            "active_page": "housing",
            "demographics": DEMOGRAPHIC_DATA,
            "rent_dollar_splits": RENT_DOLLAR_SPLITS,
            "ownership_ladder": OWNERSHIP_LADDER,
            "mega_landlords": MEGA_LANDLORDS,
            "swaps": HOUSING_SWAPS,
        },
    )
