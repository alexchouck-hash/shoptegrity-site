"""Community Commons and tip-line router.

GET handlers are read-only. Public output includes only rows with status
"published". POST handlers save new rows as "pending".
"""

from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from api.app.db.session import get_db
from api.app.models.community import RollupTip
from api.app.services.community_service import (
    WITHHELD,
    get_discussion_rooms,
    get_room,
    get_published_articles,
    get_published_article_by_slug,
    get_published_comments,
    get_published_tips,
    ensure_topic_row,
    add_comment,
    add_rollup_tip,
    get_impact_summary,
)

templates_dir = Path(__file__).resolve().parent.parent.parent.parent / "web" / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

router = APIRouter(tags=["Community & Field Journal"])


def _public_tip(tip: RollupTip) -> dict:
    """Public shape of a tip. Acquirer and notes are withheld until they have a cited source."""
    return {
        "id": tip.id,
        "business_name": tip.business_name,
        "service_category": tip.service_category,
        "city": tip.city,
        "state": tip.state,
        "suspected_acquirer": WITHHELD,
        "evidence_notes": WITHHELD,
        "status": tip.status,
        "created_at": tip.created_at.isoformat() if tip.created_at else None,
    }


# --- Web Portal HTML Routes ---

@router.get("/community", response_class=HTMLResponse)
def community_hub_view(request: Request, db: Session = Depends(get_db)):
    """Commons page. Read-only: nothing is written on GET."""
    rooms = get_discussion_rooms()
    topic_comments = {room.slug: get_published_comments(db, room.slug) for room in rooms}

    return templates.TemplateResponse(
        request=request,
        name="community.html",
        context={
            "active_page": "community",
            "topics": rooms,
            "topic_comments": topic_comments,
            "recent_tips": get_published_tips(db, limit=8),
            "impact": get_impact_summary(db),
        },
    )


@router.get("/community/journal/{slug}", response_class=HTMLResponse)
def article_detail_view(slug: str):
    """Field Journal article pages are withheld on this copy. Every slug returns 404."""
    raise HTTPException(status_code=404, detail="Journal article not found.")


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
    """Save a tip-line submission as pending. It is not shown publicly."""
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
    """Save a discussion comment as pending. It is not shown publicly."""
    room = get_room(topic_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Discussion room not found.")

    add_comment(
        db=db,
        topic_id=ensure_topic_row(db, room),
        author_name=author_name.strip(),
        author_location=author_location.strip() if author_location else None,
        content=content.strip(),
        swap_story=swap_story.strip() if swap_story else None,
        dollars_diverted=dollars_diverted or 0.0,
    )
    return RedirectResponse(url=f"/community?topic_id={room.slug}#discussions", status_code=303)


# --- REST API Endpoints ---

@router.get("/v1/community/articles")
def api_list_articles(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    """Published Field Journal articles. None are published on this copy."""
    articles = get_published_articles(db, limit=limit)
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
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in articles
    ]


@router.get("/v1/community/articles/{slug}")
def api_get_article(slug: str, db: Session = Depends(get_db)):
    """A published Field Journal article. Unpublished or unknown slugs return 404."""
    article = get_published_article_by_slug(db, slug)
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
        "created_at": article.created_at.isoformat() if article.created_at else None,
    }


@router.get("/v1/community/tips")
def api_list_rollup_tips(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """Published tip-line reports only. Pending submissions are never listed."""
    return [_public_tip(t) for t in get_published_tips(db, limit=limit)]


@router.get("/v1/community/impact")
def api_get_community_impact(db: Session = Depends(get_db)):
    """Impact counts over published rows only."""
    return get_impact_summary(db)
