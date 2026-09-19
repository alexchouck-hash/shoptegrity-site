from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, Request, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_

from api.app.db.session import get_db
from api.app.models.core import Brand, Entity, SpendCategory, Alternative, Place, Maker, FlowProfile
from api.app.routers.food_chain import SOURCING_LADDER, fetch_food_dollar_splits
from api.app.routers.swaps import get_swap_guide_detail
from api.app.services.geo_flow_service import SCENARIOS_META, trace_dollar_flow
from api.app.services.scoring_service import score_entity, get_cached_rubric

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
        brand_summaries.append({
            "id": b.id,
            "name": b.name,
            "slug": b.slug,
            "description": b.description,
            "parent_company_name": b.entity.name,
            "ownership_type": b.entity.ownership_type.replace('_', ' ').title(),
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
            "parent_name": alt.to_brand.entity.name,
            "ownership_type": alt.to_brand.entity.ownership_type,
            "composite_score": target_score.composite_score,
            "rationale": alt.rationale,
            "price_band": alt.price_band,
            "where_to_buy": alt.where_to_buy,
            "savings_estimate": alt.savings_estimate,
        })

    evidence_list = [
        {
            "dimension": ev.dimension,
            "fact_text": ev.fact_text,
            "source_url": ev.source_url,
            "source_name": ev.source_name,
        }
        for ev in entity.evidence_items
        if ev.status == "published"
    ]

    brand_data = {
        "id": brand.id,
        "name": brand.name,
        "slug": brand.slug,
        "description": brand.description,
        "website": brand.website,
        "parent_entity": {
            "name": entity.name,
            "ownership_type": entity.ownership_type.replace('_', ' ').title(),
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
        },
    )


@router.get("/local", response_class=HTMLResponse)
def local_view(request: Request, db: Session = Depends(get_db)):
    places = db.query(Place).all()
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


@router.get("/parents", response_class=HTMLResponse)
def parents_view(
    request: Request,
    q: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    subterfuge: Optional[str] = Query(None),
):
    from api.app.services.parent_lookup_service import parent_service

    is_subterfuge = True if subterfuge == "true" else None
    feed_data = parent_service.get_feed(
        q=q,
        category=category,
        is_surprising=is_subterfuge,
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
            "subterfuge_only": is_subterfuge,
        },
    )

