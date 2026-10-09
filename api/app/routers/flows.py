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


HISTORICAL_DFA_TIMELINE = {
    "source": "Federal Reserve Distributional Financial Accounts (DFA) & Institutional Disclosures",
    "description": "Historical concentration of U.S. Corporate Equities and Mutual Fund Shares (1989-Present) vs Big Three (BlackRock, Vanguard, State Street) AUM.",
    "datapoints": [
        {"year": 1989, "top_1_pct": 38.6, "top_10_pct": 81.7, "middle_40_pct": 14.4, "bottom_50_pct": 3.9, "big_three_aum_trillions": 0.08, "milestone": "401(k) expansion replaces pensions; automated paycheck deductions start flowing to Wall Street."},
        {"year": 1995, "top_1_pct": 42.1, "top_10_pct": 84.5, "middle_40_pct": 12.8, "bottom_50_pct": 2.7, "big_three_aum_trillions": 0.45, "milestone": "Dot-com boom; retail mutual funds surge; financial deregulation accelerates."},
        {"year": 2001, "top_1_pct": 45.3, "top_10_pct": 85.1, "middle_40_pct": 13.1, "bottom_50_pct": 1.8, "big_three_aum_trillions": 1.40, "milestone": "Repeal of Glass-Steagall enables commercial banks to merge with speculative investment houses."},
        {"year": 2008, "top_1_pct": 47.8, "top_10_pct": 86.2, "middle_40_pct": 12.4, "bottom_50_pct": 1.4, "big_three_aum_trillions": 4.80, "milestone": "Financial Crisis: Wall Street bailed out; BlackRock acquires iShares to become world's largest asset manager."},
        {"year": 2015, "top_1_pct": 49.5, "top_10_pct": 88.1, "middle_40_pct": 10.8, "bottom_50_pct": 1.1, "big_three_aum_trillions": 11.20, "milestone": "Near-zero interest rates fuel trillions in corporate debt-funded share buybacks and private equity rollups."},
        {"year": 2020, "top_1_pct": 52.4, "top_10_pct": 89.2, "middle_40_pct": 9.9, "bottom_50_pct": 0.9, "big_three_aum_trillions": 17.50, "milestone": "Pandemic stimulus & Fed bond buying drive historic equity rally; Top 1% equity share crosses 50% for first time."},
        {"year": 2026, "top_1_pct": 54.2, "top_10_pct": 91.3, "middle_40_pct": 8.1, "bottom_50_pct": 0.6, "big_three_aum_trillions": 24.20, "milestone": "Big Three manage over $24 Trillion, casting ~80% of institutional proxy votes across the S&P 500."},
    ],
    "historical_precedents": [
        {
            "era": "The Late Roman Republic (133 BCE)",
            "problem": "Latifundia mega-estates swallowed family farms using debt and captive labor, concentrating land in the Senatorial elite.",
            "solution_attempted": "The Gracchi Brothers pushed Lex Sempronia Agraria to redistribute land. The senatorial oligarchy assassinated them, triggering civil wars that ended the Republic.",
            "lesson": "Ignoring extreme concentration leads to institutional collapse."
        },
        {
            "era": "The American Gilded Age (1890–1914)",
            "problem": "Standard Oil, J.P. Morgan, and railroad trusts controlled national commerce and fixed consumer prices.",
            "solution_attempted": "Bipartisan antitrust action: Sherman Act (1890), Clayton Act (1914), and Teddy Roosevelt's aggressive trust-busting broke up Standard Oil and Northern Securities.",
            "lesson": "Legal antitrust enforcement and breaking monopolistic holding structures works."
        },
        {
            "era": "The Swedish Co-op Revolt (1920s–1930s)",
            "problem": "Private industrial cartels locked food and consumer goods prices in early 20th century Scandinavia.",
            "solution_attempted": "Kooperativa Förbundet (KF) rallied working-class families to build their own flour mills and lightbulb factories, bankrupting the cartels through cooperative competition.",
            "lesson": "Consumers organizing cooperative supply chains can dismantle monopolies without waiting for politicians."
        }
    ]
}


@router.get("/macro-timeline/data")
def get_macro_timeline():
    """Returns Federal Reserve DFA historical equity concentration (1989-present) and historical parallels."""
    return HISTORICAL_DFA_TIMELINE


