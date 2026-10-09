"""Community, Field Journal, and Crowdsourced Tip-Line Router."""

from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from api.app.db.session import get_db
from api.app.services.community_service import (
    seed_community_data,
    get_articles,
    get_article_by_slug,
    get_topics,
    get_topic_by_slug,
    add_comment,
    add_rollup_tip,
    get_recent_tips,
    get_impact_summary,
)

templates_dir = Path(__file__).resolve().parent.parent.parent.parent / "web" / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

router = APIRouter(tags=["Community & Field Journal"])


# --- Web Portal HTML Routes ---

@router.get("/community", response_class=HTMLResponse)
def community_hub_view(request: Request, db: Session = Depends(get_db)):
    """Main Community Commons: Field Journal, Whistleblower Desk, and Action Discussions."""
    seed_community_data(db)
    articles = get_articles(db, limit=6)
    topics = get_topics(db)
    recent_tips = get_recent_tips(db, limit=8)
    impact = get_impact_summary(db)

    return templates.TemplateResponse(
        request=request,
        name="community.html",
        context={
            "active_page": "community",
            "articles": articles,
            "topics": topics,
            "recent_tips": recent_tips,
            "impact": impact,
        },
    )


@router.get("/community/journal/{slug}", response_class=HTMLResponse)
def article_detail_view(request: Request, slug: str, db: Session = Depends(get_db)):
    """Read a full Field Journal investigative article."""
    seed_community_data(db)
    article = get_article_by_slug(db, slug)
    if not article:
        raise HTTPException(status_code=404, detail="Journal article not found.")

    related_articles = [a for a in get_articles(db, limit=4) if a.slug != slug][:3]

    return templates.TemplateResponse(
        request=request,
        name="article_detail.html",
        context={
            "active_page": "community",
            "article": article,
            "related_articles": related_articles,
        },
    )


@router.post("/community/tips")
def submit_rollup_tip_form(
    business_name: str = Form(...),
    service_category: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    suspected_acquirer: str = Form(...),
    evidence_notes: str = Form(...),
    db: Session = Depends(get_db),
):
    """Handle crowdsourced PE rollup whistleblower tip submission."""
    add_rollup_tip(
        db=db,
        business_name=business_name.strip(),
        service_category=service_category.strip(),
        city=city.strip(),
        state=state.strip().upper(),
        suspected_acquirer=suspected_acquirer.strip(),
        evidence_notes=evidence_notes.strip(),
    )
    return RedirectResponse(url="/community?tip_submitted=true#whistleblower", status_code=303)


@router.post("/community/discussions/{topic_id}/comments")
def post_topic_comment_form(
    topic_id: str,
    author_name: str = Form(...),
    author_location: Optional[str] = Form(None),
    content: str = Form(...),
    swap_story: Optional[str] = Form(None),
    dollars_diverted: Optional[float] = Form(0.0),
    db: Session = Depends(get_db),
):
    """Submit a response / swap impact story to an ongoing discussion room."""
    add_comment(
        db=db,
        topic_id=topic_id,
        author_name=author_name.strip(),
        author_location=author_location.strip() if author_location else None,
        content=content.strip(),
        swap_story=swap_story.strip() if swap_story else None,
        dollars_diverted=dollars_diverted or 0.0,
    )
    return RedirectResponse(url=f"/community?topic_id={topic_id}#discussions", status_code=303)


# --- REST API Endpoints ---

@router.get("/v1/community/articles")
def api_list_articles(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    """API list of investigative journal articles."""
    seed_community_data(db)
    articles = get_articles(db, limit=limit)
    return [
        {
            "id": a.id,
            "slug": a.slug,
            "title": a.title,
            "subtitle": a.subtitle,
            "category": a.category,
            "author": a.author,
            "read_time": a.read_time,
            "hero_icon": a.hero_icon,
            "created_at": a.created_at.isoformat(),
        }
        for a in articles
    ]


@router.get("/v1/community/articles/{slug}")
def api_get_article(slug: str, db: Session = Depends(get_db)):
    """API retrieve a single article with full HTML body."""
    seed_community_data(db)
    article = get_article_by_slug(db, slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found.")
    return {
        "id": article.id,
        "slug": article.slug,
        "title": article.title,
        "subtitle": article.subtitle,
        "category": article.category,
        "author": article.author,
        "read_time": article.read_time,
        "body_html": article.body_html,
        "created_at": article.created_at.isoformat(),
    }


@router.get("/v1/community/tips")
def api_list_rollup_tips(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """API list of verified and reported private equity rollups."""
    seed_community_data(db)
    tips = get_recent_tips(db, limit=limit)
    return [
        {
            "id": t.id,
            "business_name": t.business_name,
            "service_category": t.service_category,
            "city": t.city,
            "state": t.state,
            "suspected_acquirer": t.suspected_acquirer,
            "evidence_notes": t.evidence_notes,
            "status": t.status,
            "created_at": t.created_at.isoformat(),
        }
        for t in tips
    ]


@router.get("/v1/community/impact")
def api_get_community_impact(db: Session = Depends(get_db)):
    """API retrieve total community impact metrics (tips submitted, dollars diverted)."""
    seed_community_data(db)
    return get_impact_summary(db)
