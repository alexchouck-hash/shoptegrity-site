from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class EvidenceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dimension: str
    fact_text: str
    source_url: str
    source_name: str
    source_type: str
    event_date: Optional[str] = None
    retrieved_at: str
    impact: int
    status: str


class DimensionScoreSchema(BaseModel):
    key: str
    name: str
    value: Optional[float]
    confidence: float
    status: str
    weight: float
    explanation: str
    evidence: List[EvidenceSchema] = []


class EntityScoreSummary(BaseModel):
    id: str
    name: Optional[str] = None  # None until ownership is cited (sourced-or-withheld)
    slug: str
    ownership_type: Optional[str] = None
    hq_city: Optional[str] = None
    hq_state: Optional[str] = None
    locality_tier: str
    composite_score: Optional[float] = None
    confidence: float
    dimensions: Dict[str, DimensionScoreSchema] = {}


class BrandSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    description: Optional[str] = None  # withheld: no citation field exists for descriptions
    category_tags: List[str] = []
    parent_company_name: Optional[str] = None  # None until ownership is cited
    parent_company_slug: Optional[str] = None
    ownership_type: Optional[str] = None
    composite_score: Optional[float] = None
    confidence: float


class AlternativeCard(BaseModel):
    id: str
    brand_name: str
    brand_slug: str
    parent_name: Optional[str] = None
    ownership_type: Optional[str] = None
    composite_score: Optional[float]
    rationale: Optional[str] = None  # withheld until cited
    price_band: Optional[str] = None
    where_to_buy: Optional[str] = None
    savings_estimate: Optional[str] = None
    swap_tier: str = "best"
    similarity_notes: Optional[str] = None


class BrandDetail(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None  # withheld: no citation field exists for descriptions
    website: Optional[str] = None
    category_tags: List[str] = []
    parent_entity: EntityScoreSummary
    scorecard: Dict[str, DimensionScoreSchema]
    composite_score: Optional[float]
    confidence: float
    evidence: List[EvidenceSchema]
    alternatives: List[AlternativeCard] = []


class PlaceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    category: str
    address: str
    city: str
    state: str
    postal_code: str
    lat: float
    lon: float
    phone: Optional[str] = None
    website: Optional[str] = None
    ownership_tier: int
    flags: List[str] = []
    verified_locally: bool
    verified_how: str
    hours: Optional[str] = None
    season: Optional[str] = None
    distance_km: Optional[float] = None


class MakerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    products: List[str]
    makes_own: bool
    makes_own_evidence: str
    certifications: List[str]
    sourcing_ladder_tier: int
    where_to_buy: str
    direct_order_url: Optional[str] = None
    place: Optional[PlaceSummary] = None


class FlowProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    spend_category_id: str
    option_type: str
    display_title: str
    year: int
    nodes_json: Dict[str, Any]
    summary_text: str
    source_notes: str


class SpendCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    tier: int
    avg_annual_spend: float
    swap_difficulty: str
    saves_money: bool
    description: str


class FoodDollarSplit(BaseModel):
    product_category: str
    farm_share_cents: float
    food_processing_cents: float
    packaging_cents: float
    transportation_cents: float
    wholesale_trade_cents: float
    retail_trade_cents: float
    food_services_cents: float
    energy_cents: float
    finance_insurance_cents: float
    advertising_cents: float
    other_cents: float
    year: int
    source_citation: str
    summary_insight: str


class FarmGateCostItem(BaseModel):
    name: str
    amount: float
    percentage_of_farm_gate: float
    corporate_beneficiaries: List[str]
    is_farmer_take_home: bool = False
    color_code: Optional[str] = None


class FarmGateAudit(BaseModel):
    farm_type: str  # contract_grower, conventional_commodity, community_farmer
    title: str
    gross_farm_gate_amount: float
    input_expenses: List[FarmGateCostItem]
    net_farmer_take_home_amount: float
    net_farmer_take_home_pct: float
    notes: str


class EliteLandownerProfile(BaseModel):
    name: str
    rank: int
    acreage: int
    acreage_display: str
    primary_holdings: str
    water_and_resource_notes: str


class FarmlandOwnershipStats(BaseModel):
    total_us_farmland_acres: str
    rented_percentage: float
    rented_acres: str
    non_operator_landlord_pct: float
    non_operators_never_farmed_pct: float
    corn_belt_rented_pct_range: str
    owner_operator_pct: float
    institutional_investor_pct: float
    foreign_investor_pct: float
    top_100_landowners_pct: float
    top_elite_landowners: List[EliteLandownerProfile]
    sources: List[str]


class GeoFlowNode(BaseModel):
    role: str
    payee_name: str
    destination_zip: str
    city: str
    state: str
    lat: float
    lon: float
    amount: float
    percentage: float
    distance_miles: float
    is_local: bool
    leak_category: str  # local_community, regional_steward, corporate_overhead, wall_street_leak
    farm_ownership_tier: Optional[str] = None  # community_farmer, contract_grower, corporate_agribusiness, not_farm
    farm_ownership_notes: Optional[str] = None
    farm_gate_audit: Optional[FarmGateAudit] = None


class GeoFlowBranch(BaseModel):
    option_type: str  # conventional vs alternative
    display_title: str
    nodes: List[GeoFlowNode]
    total_spend: float
    local_retained_amount: float
    local_retained_pct: float
    capital_flight_amount: float
    capital_flight_pct: float
    worker_farmer_amount: float
    worker_farmer_pct: float
    operations_logistics_amount: float
    operations_logistics_pct: float
    executive_shareholder_amount: float
    executive_shareholder_pct: float
    member_dividends_amount: float = 0.0
    member_dividends_pct: float = 0.0
    avg_miles_traveled: float
    summary_text: str



class GeoFlowScenarioSummary(BaseModel):
    id: str
    name: str
    category: str
    description: str


class GeoFlowTraceResponse(BaseModel):
    origin_zip: str
    origin_city: str
    origin_state: str
    origin_lat: float
    origin_lon: float
    spend_amount: float
    scenario_id: str
    scenario_title: str
    conventional: GeoFlowBranch
    alternative: GeoFlowBranch
    comparison_insight: str

