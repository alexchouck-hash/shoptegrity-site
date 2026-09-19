from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.app.db.session import get_db
from api.app.models.core import FlowProfile, SpendCategory
from api.app.schemas.domain import (
    FlowProfileRead,
    GeoFlowScenarioSummary,
    GeoFlowTraceResponse,
)
from api.app.services.geo_flow_service import (
    SCENARIOS_META,
    trace_dollar_flow,
)

router = APIRouter(prefix="/v1/flows", tags=["Dollar Flow Map"])


@router.get("/geo/scenarios", response_model=List[GeoFlowScenarioSummary])
def get_geo_scenarios():
    """Returns available purchasing scenarios for geographic dollar flow tracing."""
    return SCENARIOS_META


@router.get("/geo/trace", response_model=GeoFlowTraceResponse)
def trace_geo_dollar_flow(
    origin_zip: str = Query("55401", description="Consumer 5-digit US ZIP code", min_length=5, max_length=5),
    scenario_id: str = Query("grocery_produce", description="Scenario ID (e.g. grocery_produce, meat_poultry, banking_services, home_services)"),
    spend: float = Query(100.0, description="Amount spent in dollars", gt=0),
):
    """Calculates where a dollar physically travels by ZIP code, comparing corporate vs community flows."""
    return trace_dollar_flow(origin_zip=origin_zip, scenario_id=scenario_id, spend_amount=spend)


@router.get("/{category_id}", response_model=List[FlowProfileRead])
def get_flow_profiles_by_category(category_id: str, db: Session = Depends(get_db)):
    """Returns side-by-side $100 spending flow profiles (conventional vs high-integrity alternative)."""
    profiles = db.query(FlowProfile).filter(FlowProfile.spend_category_id == category_id).all()
    if not profiles:
        raise HTTPException(status_code=404, detail=f"No flow profile found for category '{category_id}'")
    return profiles

