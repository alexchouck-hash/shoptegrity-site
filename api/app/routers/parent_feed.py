"""REST API Router for the Brand & Product Feed.

Ownership is withheld until each claim has a cited source. Every response and
download passes through public_record() or _public_stats(), so no subterfuge or
enrichment field is served and the parent-company fields are always null.
"""

import csv
import io
import json
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from api.app.services.parent_lookup_service import parent_service

router = APIRouter(prefix="/v1/feed/parents", tags=["Brand & Product Parent Feed"])

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
JSON_FILE = DATA_DIR / "brand_parent_feed.json"
CSV_FILE = DATA_DIR / "brand_parent_feed.csv"

WITHHELD = "Withheld: no cited source yet"
OWNERSHIP_FIELDS = ("parent_company", "ultimate_parent", "ownership_type", "ticker_or_jurisdiction")
WITHDRAWN_KEY_MARKERS = ("subterfuge", "enrichment", "siphon", "surprising")


def _is_withdrawn_key(key: Any) -> bool:
    """True for any field name that belongs to a withdrawn judgment or statistic."""
    k = str(key).lower()
    return any(marker in k for marker in WITHDRAWN_KEY_MARKERS)


def public_record(item: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of a feed record with withdrawn fields removed and ownership withheld."""
    rec = {k: v for k, v in item.items() if not _is_withdrawn_key(k)}
    for field in OWNERSHIP_FIELDS:
        rec[field] = None
    rec["ownership_status"] = WITHHELD
    rec["ethical_swap_recommendation"] = WITHHELD
    return rec


def _public_stats(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Drop withdrawn statistics and withhold parent-company rollups."""
    out = {k: v for k, v in stats.items() if not _is_withdrawn_key(k)}
    out["top_parent_conglomerates"] = []
    out["ownership_status"] = WITHHELD
    return out


@router.get("")
def get_parent_feed(
    q: Optional[str] = Query(None, description="Search term for product or brand name"),
    category: Optional[str] = Query(None, description="Filter by category"),
    parent: Optional[str] = Query(None, description="Filter by parent company (withheld: no cited source yet, so no record matches)"),
    item_type: Optional[str] = Query(None, description="Filter by 'brand' or 'product'"),
    limit: int = Query(50, ge=1, le=1000, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Offset index for pagination"),
):
    """List brand and product records. Ownership fields are withheld until cited."""
    if parent:
        # Parent names are withheld, so no record can match a parent filter.
        # The lookup service would fail on null parent fields, so it is not called here.
        return {
            "total": 0,
            "offset": offset,
            "limit": limit,
            "results": [],
            "parent_filter": WITHHELD,
        }
    res = parent_service.get_feed(
        q=q,
        category=category,
        item_type=item_type,
        limit=limit,
        offset=offset,
    )
    return {
        **res,
        "results": [public_record(r) for r in res["results"]],
    }


@router.get("/lookup")
def lookup_brand_or_product(
    query: str = Query(..., min_length=1, description="Brand or product name to look up"),
):
    """Look up a brand or product by name. Parent-company and ownership fields are withheld until cited."""
    match = parent_service.lookup(query)
    if not match:
        raise HTTPException(
            status_code=404,
            detail=f"Brand or product '{query}' not found in the feed.",
        )
    return {
        "query": query,
        "match": public_record(match),
    }


@router.get("/stats")
def get_feed_statistics():
    """Summary counts for the brand and product feed. Parent-company rollups are withheld."""
    return _public_stats(parent_service.get_stats())


@router.get("/download/json")
def download_json_feed():
    """Download the brand and product feed in JSON, with ownership withheld."""
    if not JSON_FILE.exists():
        raise HTTPException(status_code=404, detail="JSON feed file not generated.")
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        records = [public_record(r) for r in json.load(f)]
    return Response(
        content=json.dumps(records, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="brand_parent_feed.json"'},
    )


@router.get("/download/csv")
def download_csv_feed():
    """Download the brand and product feed in CSV, with ownership withheld."""
    if not CSV_FILE.exists():
        raise HTTPException(status_code=404, detail="CSV feed file not generated.")
    with open(CSV_FILE, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = [c for c in (reader.fieldnames or []) if not _is_withdrawn_key(c)]
        rows = [public_record(row) for row in reader]
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="brand_parent_feed.csv"'},
    )
