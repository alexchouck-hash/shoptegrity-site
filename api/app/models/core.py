"""Core SQLAlchemy 2.0 database models for Shoptegrity.

Shared across the Brand Integrity site, Food Chain partner site,
Local Directory, and the MCP server.
"""

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
    JSON,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Entity(Base):
    """Represents a corporate entity, holding company, cooperative, PE firm, or producer."""

    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(50))  # company, brand, pe_firm, cooperative, nonprofit
    ownership_type: Mapped[str] = mapped_column(String(50))  # worker_coop, public, private_equity, etc.
    parent_entity_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("entities.id"), nullable=True
    )
    hq_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    hq_state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    hq_country: Mapped[str] = mapped_column(String(100), default="USA")
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    ticker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Scored metrics
    ceo_pay_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    capital_extraction_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    locality_tier: Mapped[str] = mapped_column(String(50), default="national_public")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    parent: Mapped[Optional["Entity"]] = relationship(
        "Entity", remote_side=[id], backref="subsidiaries"
    )
    brands: Mapped[List["Brand"]] = relationship("Brand", back_populates="entity")
    evidence_items: Mapped[List["Evidence"]] = relationship("Evidence", back_populates="entity")
    places: Mapped[List["Place"]] = relationship("Place", back_populates="entity")


class Brand(Base):
    """Consumer brand (e.g. Annie's, Seventh Generation, Dr. Bronner's)."""

    __tablename__ = "brands"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"))
    description: Mapped[str] = mapped_column(Text, default="")
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    category_tags: Mapped[List[str]] = mapped_column(JSON, default=list)

    # Relationship
    entity: Mapped[Entity] = relationship("Entity", back_populates="brands")


class SpendCategory(Base):
    """High-level household budget category (e.g. Grocery, Banking, Clothing)."""

    __tablename__ = "spend_categories"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    tier: Mapped[int] = mapped_column(Integer, default=1)
    avg_annual_spend: Mapped[float] = mapped_column(Float, default=0.0)
    swap_difficulty: Mapped[str] = mapped_column(String(20), default="easy")
    saves_money: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str] = mapped_column(Text, default="")


class Evidence(Base):
    """Verifiable, cited fact or regulatory record linked to an entity."""

    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"), index=True)
    dimension: Mapped[str] = mapped_column(String(50), index=True)
    fact_text: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(500))
    source_name: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(50))  # sec_edgar, osha, epa, certifier, etc.
    event_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    retrieved_at: Mapped[str] = mapped_column(String(50))
    impact: Mapped[int] = mapped_column(Integer, default=0)  # -2 to +2
    status: Mapped[str] = mapped_column(String(20), default="published")
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    entity: Mapped[Entity] = relationship("Entity", back_populates="evidence_items")


class Alternative(Base):
    """Curated swap recommendation from a conventional brand to a higher-integrity option."""

    __tablename__ = "alternatives"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    from_brand_id: Mapped[str] = mapped_column(String(36), ForeignKey("brands.id"), index=True)
    to_brand_id: Mapped[str] = mapped_column(String(36), ForeignKey("brands.id"))
    spend_category_id: Mapped[str] = mapped_column(String(50), ForeignKey("spend_categories.id"))
    rationale: Mapped[str] = mapped_column(Text)
    price_band: Mapped[str] = mapped_column(String(10), default="$$")  # $, $$, $$$
    where_to_buy: Mapped[str] = mapped_column(String(255))
    savings_estimate: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    editor_approved: Mapped[bool] = mapped_column(Boolean, default=True)

    from_brand: Mapped[Brand] = relationship("Brand", foreign_keys=[from_brand_id])
    to_brand: Mapped[Brand] = relationship("Brand", foreign_keys=[to_brand_id])


class FlowProfile(Base):
    """Spending breakdown profile ($100 spent at Company A vs Company B)."""

    __tablename__ = "flow_profiles"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    spend_category_id: Mapped[str] = mapped_column(String(50), ForeignKey("spend_categories.id"))
    option_type: Mapped[str] = mapped_column(String(20))  # "conventional" or "alternative"
    display_title: Mapped[str] = mapped_column(String(255))
    entity_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("entities.id"), nullable=True)
    year: Mapped[int] = mapped_column(Integer, default=2024)
    # JSON node allocations of $100
    nodes_json: Mapped[dict] = mapped_column(JSON)
    summary_text: Mapped[str] = mapped_column(Text)
    source_notes: Mapped[str] = mapped_column(Text)


class Place(Base):
    """Physical location: farm, co-op, farmers market, credit union, local service."""

    __tablename__ = "places"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(50), index=True)  # farmers_market, food_coop, csa, plumber, etc.
    address: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(100), index=True)
    state: Mapped[str] = mapped_column(String(50), index=True)
    postal_code: Mapped[str] = mapped_column(String(20), index=True)
    lat: Mapped[float] = mapped_column(Float, index=True)
    lon: Mapped[float] = mapped_column(Float, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    entity_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("entities.id"), nullable=True)
    ownership_tier: Mapped[int] = mapped_column(Integer, default=0)  # 0=unknown, 1=owner-operated, ..., 6=PE/Public
    flags: Mapped[List[str]] = mapped_column(JSON, default=list)  # ["coop", "rollup_disguised", "snap_ebt", "organic"]
    verified_locally: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_how: Mapped[str] = mapped_column(String(255), default="Unverified")
    hours: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    season: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    entity: Mapped[Optional[Entity]] = relationship("Entity", back_populates="places")
    maker: Mapped[Optional["Maker"]] = relationship("Maker", back_populates="place", uselist=False)


class Maker(Base):
    """Small producer, grower, roaster, or artisan with 'makes own' verification."""

    __tablename__ = "makers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), index=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("entities.id"), nullable=True)
    place_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("places.id"), nullable=True)
    products: Mapped[List[str]] = mapped_column(JSON, default=list)  # ["Tea", "Honey", "Apples"]
    makes_own: Mapped[bool] = mapped_column(Boolean, default=True)
    makes_own_evidence: Mapped[str] = mapped_column(Text)
    certifications: Mapped[List[str]] = mapped_column(JSON, default=list)
    sourcing_ladder_tier: Mapped[int] = mapped_column(Integer, default=3)  # Tier 3 = direct farm/maker
    where_to_buy: Mapped[str] = mapped_column(String(255))
    direct_order_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    place: Mapped[Optional[Place]] = relationship("Place", back_populates="maker")


class BrandIntegrity(Base):
    """Top 2,000 brands database with measured financial splits, labor exploitation, and waste metrics."""

    __tablename__ = "brand_integrity"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    parent_company: Mapped[str] = mapped_column(String(255), index=True)
    ownership_type: Mapped[str] = mapped_column(String(50), index=True)  # worker_coop, esop, public, private_equity, etc.
    composite_score: Mapped[int] = mapped_column(Integer, index=True)  # 0 - 100
    grade: Mapped[str] = mapped_column(String(5), index=True)  # A+, A, B, C, D, F

    # Where the money goes ($100 breakdown)
    worker_wages_pct: Mapped[float] = mapped_column(Float)
    exec_comp_pct: Mapped[float] = mapped_column(Float)
    shareholder_extraction_pct: Mapped[float] = mapped_column(Float)
    marketing_ads_pct: Mapped[float] = mapped_column(Float)
    cogs_supply_pct: Mapped[float] = mapped_column(Float)
    retained_operations_pct: Mapped[float] = mapped_column(Float)

    # Labor Exploitation
    labor_exploitation_rating: Mapped[str] = mapped_column(String(50), index=True)  # Fair, Low, Moderate, High, Severe
    sweatshop_risk: Mapped[str] = mapped_column(String(50))
    osha_violations_count: Mapped[int] = mapped_column(Integer, default=0)
    nlrb_complaints_count: Mapped[int] = mapped_column(Integer, default=0)
    living_wage_certified: Mapped[bool] = mapped_column(Boolean, default=False)
    labor_summary: Mapped[str] = mapped_column(Text)

    # Waste & Packaging
    waste_rating: Mapped[str] = mapped_column(String(50), index=True)  # Circular, Low Waste, Moderate, High Single-Use, Severe
    packaging_type: Mapped[str] = mapped_column(String(100))
    repairability_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-10
    landfill_diverted_pct: Mapped[float] = mapped_column(Float, default=0.0)
    waste_summary: Mapped[str] = mapped_column(Text)

    # Recommended Swap
    swap_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    swap_slug: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    swap_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Retailer Specifics
    is_major_retailer: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    retailer_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
