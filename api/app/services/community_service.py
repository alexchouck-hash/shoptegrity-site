"""Community service: discussion rooms, tip-line, and public impact counts.

Read paths never write. Submissions are saved with status "pending". Public
output includes only rows whose status is "published". No code path in this
module publishes a row, so on this copy every public list is empty and every
impact tile reads "None published yet".

Field Journal articles are withheld on this copy. No article content lives in
code, and the article routes return 404.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from sqlalchemy import false, func
from sqlalchemy.orm import Session

from api.app.models.community import (
    JournalArticle,
    DiscussionTopic,
    DiscussionComment,
    RollupTip,
)
from api.app.models.core import generate_uuid


PUBLISHED = "published"
PENDING = "pending"

# Shown in place of any ownership, acquirer, or allegation text that has no cited source.
WITHHELD = "Withheld: no cited source yet"


@dataclass(frozen=True)
class DiscussionRoom:
    """An action room in the Commons. Room definitions are code, not stored content."""

    slug: str
    title: str
    category: str
    description: str


DISCUSSION_ROOMS: List[DiscussionRoom] = [
    DiscussionRoom(
        slug="credit-union-migration-stories",
        title="Credit Union Migration: Moving Money Out of Wall Street",
        category="Banking & Finance",
        description="Have you moved your accounts from a large national bank to a credit union or community development financial institution (CDFI)? Share your experience and advice for others considering the same move.",
    ),
    DiscussionRoom(
        slug="pe-acquisition-tip-desk",
        title="Tip Desk: Possible Private Equity Acquisitions",
        category="Local Services & Trades",
        description="Have you noticed a local HVAC company, vet clinic, or plumber change its name, pricing, or sales practices? Describe what you observed. Reader reports are unverified.",
    ),
    DiscussionRoom(
        slug="csa-direct-farm-playbook",
        title="Direct Farm & CSA Sourcing: Cutting Out the Grocery Middleman",
        category="Food Chain Integrity",
        description="How do you source directly from local growers? Share your favorite regional CSAs, farm stands, and bulk buying clubs.",
    ),
    DiscussionRoom(
        slug="401k-proxy-voting-reform",
        title="Your 401(k): Proxy Voting and Fund Options",
        category="Retirement & Policy",
        description="How can you ask your HR department how plan shares are voted, and whether worker-owned or other index options can be added to your employer's retirement plan?",
    ),
]


def _has_status(model) -> bool:
    return getattr(model, "status", None) is not None


def _public_filter(model):
    """SQL filter for publicly visible rows. A model without a status column has none."""
    if not _has_status(model):
        return false()
    return model.status == PUBLISHED


def get_discussion_rooms() -> List[DiscussionRoom]:
    return list(DISCUSSION_ROOMS)


def get_room(slug: str) -> Optional[DiscussionRoom]:
    return next((room for room in DISCUSSION_ROOMS if room.slug == slug), None)


# --- Field Journal (withheld: no published article exists on this copy) ---

def get_published_articles(db: Session, limit: int = 10) -> List[JournalArticle]:
    return (
        db.query(JournalArticle)
        .filter(_public_filter(JournalArticle))
        .order_by(JournalArticle.created_at.desc())
        .limit(limit)
        .all()
    )


def get_published_article_by_slug(db: Session, slug: str) -> Optional[JournalArticle]:
    return (
        db.query(JournalArticle)
        .filter(JournalArticle.slug == slug, _public_filter(JournalArticle))
        .first()
    )


# --- Discussion rooms and comments ---

def _topic_row(db: Session, slug: str) -> Optional[DiscussionTopic]:
    return db.query(DiscussionTopic).filter(DiscussionTopic.slug == slug).first()


def ensure_topic_row(db: Session, room: DiscussionRoom) -> str:
    """Return the DiscussionTopic id for a room, creating the row if needed.

    Called only from the comment POST handler, so the GET path stays read-only.
    """
    row = _topic_row(db, room.slug)
    if row is None:
        row = DiscussionTopic(
            id=generate_uuid(),
            slug=room.slug,
            title=room.title,
            category=room.category,
            description=room.description,
            created_at=datetime.now(timezone.utc),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row.id


def get_published_comments(db: Session, room_slug: str) -> List[DiscussionComment]:
    row = _topic_row(db, room_slug)
    if row is None:
        return []
    return (
        db.query(DiscussionComment)
        .filter(DiscussionComment.topic_id == row.id, _public_filter(DiscussionComment))
        .order_by(DiscussionComment.created_at.desc())
        .all()
    )


def add_comment(
    db: Session,
    topic_id: str,
    author_name: str,
    author_location: Optional[str],
    content: str,
    swap_story: Optional[str] = None,
    dollars_diverted: Optional[float] = 0.0,
) -> DiscussionComment:
    """Save a comment as pending. Pending comments are never shown publicly."""
    comment = DiscussionComment(
        id=generate_uuid(),
        topic_id=topic_id,
        author_name=author_name or "Community Member",
        author_location=author_location,
        content=content,
        swap_story=swap_story,
        estimated_dollars_diverted=dollars_diverted or 0.0,
        created_at=datetime.now(timezone.utc),
    )
    if _has_status(DiscussionComment):
        comment.status = PENDING
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


# --- Tip-line ---

def add_rollup_tip(
    db: Session,
    business_name: str,
    service_category: str,
    city: str,
    state: str,
    suspected_acquirer: str,
    evidence_notes: str,
) -> RollupTip:
    """Save a tip-line submission as pending. Pending tips are never shown publicly."""
    tip = RollupTip(
        id=generate_uuid(),
        business_name=business_name,
        service_category=service_category,
        city=city,
        state=state,
        suspected_acquirer=suspected_acquirer,
        evidence_notes=evidence_notes,
        status=PENDING,
        created_at=datetime.now(timezone.utc),
    )
    db.add(tip)
    db.commit()
    db.refresh(tip)
    return tip


def get_published_tips(db: Session, limit: int = 15) -> List[RollupTip]:
    return (
        db.query(RollupTip)
        .filter(RollupTip.status == PUBLISHED)
        .order_by(RollupTip.created_at.desc())
        .limit(limit)
        .all()
    )


# --- Impact counts (published rows only) ---

def get_impact_summary(db: Session) -> Dict[str, Any]:
    """Public impact counts. Each count includes only published rows.

    Dollar figures are self-reported comment values and are unverified. The
    "verified_rollups" key is kept for shape. It counts published tips, because
    no per-claim verification exists in the data.
    """
    published_tips = (
        db.query(func.count(RollupTip.id)).filter(RollupTip.status == PUBLISHED).scalar() or 0
    )
    published_comments = (
        db.query(func.count(DiscussionComment.id)).filter(_public_filter(DiscussionComment)).scalar() or 0
    )
    dollars_diverted = (
        db.query(func.sum(DiscussionComment.estimated_dollars_diverted))
        .filter(_public_filter(DiscussionComment))
        .scalar()
        or 0.0
    )

    return {
        "total_whistleblower_tips": published_tips,
        "verified_rollups": published_tips,
        "total_swap_stories": published_comments,
        "total_dollars_diverted": round(float(dollars_diverted), 2),
    }
