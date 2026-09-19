"""REST API Router for Brand & Product Parent Company Feed."""

from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from api.app.services.parent_lookup_service import parent_service

router = APIRouter(prefix="/v1/feed/parents", tags=["Brand & Product Parent Feed"])

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
JSON_FILE = DATA_DIR / "brand_parent_feed.json"
CSV_FILE = DATA_DIR / "brand_parent_feed.csv"


@router.get("")
def get_parent_feed(
    q: Optional[str] = Query(None, description="Search term for product or brand name"),
    category: Optional[str] = Query(None, description="Filter by category"),
    parent: Optional[str] = Query(None, description="Filter by parent company"),
    is_surprising: Optional[bool] = Query(None, description="Filter only surprising / subterfuge brands"),
    item_type: Optional[str] = Query(None, description="Filter by 'brand' or 'product'"),
    limit: int = Query(50, ge=1, le=1000, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Offset index for pagination"),
):
    """Retrieve items from the 1,000+ brand & product parent company feed."""
    return parent_service.get_feed(
        q=q,
        category=category,
        parent=parent,
        is_surprising=is_surprising,
        item_type=item_type,
        limit=limit,
        offset=offset,
    )


@router.get("/lookup")
def lookup_brand_or_product(
    query: str = Query(..., min_length=1, description="Brand or product name to identify parent company"),
):
    """Take any brand or product and instantly identify the corporate parent, subterfuge context, and ethical swap."""
    match = parent_service.lookup(query)
    if not match:
        raise HTTPException(
            status_code=404,
            detail=f"Brand or product '{query}' not found in the parent feed.",
        )
    return {
        "query": query,
        "match": match,
    }


@router.get("/stats")
def get_feed_statistics():
    """Retrieve summary statistics of corporate concentration, parent conglomerates, and subterfuge percentage."""
    return parent_service.get_stats()


@router.get("/download/json")
def download_json_feed():
    """Download the full 1,000+ brand & product parent feed in JSON format."""
    if not JSON_FILE.exists():
        raise HTTPException(status_code=404, detail="JSON feed file not generated.")
    return FileResponse(
        path=str(JSON_FILE),
        filename="brand_parent_feed.json",
        media_type="application/json",
    )


@router.get("/download/csv")
def download_csv_feed():
    """Download the full 1,000+ brand & product parent feed in CSV format."""
    if not CSV_FILE.exists():
        raise HTTPException(status_code=404, detail="CSV feed file not generated.")
    return FileResponse(
        path=str(CSV_FILE),
        filename="brand_parent_feed.csv",
        media_type="text/csv",
    )
