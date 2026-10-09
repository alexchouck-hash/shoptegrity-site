"""Community, Field Journal, and Crowdsourced Rollup Models."""

from datetime import datetime, timezone
import uuid
from typing import Optional, List
from sqlalchemy import (
    String,
    Float,
    Integer,
    Boolean,
    Text,
    ForeignKey,
    DateTime,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.models.core import Base, generate_uuid


class JournalArticle(Base):
    """Investigative articles on corporate subterfuge, historical precedents, and wealth siphoning."""

    __tablename__ = "journal_articles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    subtitle: Mapped[str] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(100), default="Investigative")
    author: Mapped[str] = mapped_column(String(100), default="Shoptegrity Research Collective")
    read_time: Mapped[str] = mapped_column(String(50), default="5 min read")
    hero_icon: Mapped[str] = mapped_column(String(20), default="📜")
    body_html: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class DiscussionTopic(Base):
    """Structured discussion rooms for action-oriented community organizing."""

    __tablename__ = "discussion_topics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    comments: Mapped[List["DiscussionComment"]] = relationship(
        "DiscussionComment", back_populates="topic", cascade="all, delete-orphan", order_by="desc(DiscussionComment.created_at)"
    )


class DiscussionComment(Base):
    """User replies and swap impact stories within a discussion topic."""

    __tablename__ = "discussion_comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    topic_id: Mapped[str] = mapped_column(String(36), ForeignKey("discussion_topics.id"), index=True)
    author_name: Mapped[str] = mapped_column(String(100), default="Community Member")
    author_location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    swap_story: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estimated_dollars_diverted: Mapped[Optional[float]] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    topic: Mapped["DiscussionTopic"] = relationship("DiscussionTopic", back_populates="comments")


class RollupTip(Base):
    """Crowdsourced tip-line reports of disguised private equity acquisitions."""

    __tablename__ = "rollup_tips"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    business_name: Mapped[str] = mapped_column(String(255))
    service_category: Mapped[str] = mapped_column(String(100))  # e.g. HVAC, Plumbing, Vet, Dental
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(50))
    suspected_acquirer: Mapped[str] = mapped_column(String(255))
    evidence_notes: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="under_investigation")  # pending, under_investigation, verified
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
