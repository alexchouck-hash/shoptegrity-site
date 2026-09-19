from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.app.db.session import get_db
from api.app.models.core import FlowProfile, SpendCategory
from api.app.schemas.domain import FlowProfileRead

router = APIRouter(prefix="/v1/flows", tags=["Dollar Flow Map"])


@router.get("/{category_id}", response_model=List[FlowProfileRead])
def get_flow_profiles_by_category(category_id: str, db: Session = Depends(get_db)):
    """Returns side-by-side $100 spending flow profiles (conventional vs high-integrity alternative)."""
    profiles = db.query(FlowProfile).filter(FlowProfile.spend_category_id == category_id).all()
    if not profiles:
        raise HTTPException(status_code=404, detail=f"No flow profile found for category '{category_id}'")
    return profiles
