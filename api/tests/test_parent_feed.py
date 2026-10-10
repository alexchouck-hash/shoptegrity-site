"""Tests for the Brand & Product Feed: files, lookup API, downloads, and MCP tools.

Ownership is withheld. Parent-company fields are null, each record says
"Withheld: no cited source yet", and no subterfuge or enrichment field exists.
"""

import json
import csv
import re
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from api.app.main import app
from api.app.services.parent_lookup_service import parent_service


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
JSON_FEED = PROJECT_ROOT / "data" / "brand_parent_feed.json"
CSV_FEED = PROJECT_ROOT / "data" / "brand_parent_feed.csv"

WITHHELD = "Withheld: no cited source yet"
OWNERSHIP_FIELDS = ("parent_company", "ultimate_parent", "ownership_type", "ticker_or_jurisdiction")
WITHDRAWN_MARKERS = ("subterfuge", "enrichment", "siphon", "surprising")


def _withdrawn_keys(obj):
    return [k for k in obj if any(m in str(k).lower() for m in WITHDRAWN_MARKERS)]


def _assert_withheld_record(rec):
    assert not _withdrawn_keys(rec), f"withdrawn fields present: {_withdrawn_keys(rec)}"
    for field in OWNERSHIP_FIELDS:
        assert rec.get(field) is None, f"{field} should be null, got {rec.get(field)!r}"
    assert rec.get("ownership_status") == WITHHELD
    assert rec.get("ethical_swap_recommendation") == WITHHELD


def test_feed_files_exist_and_contain_1000_items():
    """Verify that both JSON and CSV feeds exist and contain at least 1,000 products and brands."""
    assert JSON_FEED.exists(), "JSON feed file does not exist"
    assert CSV_FEED.exists(), "CSV feed file does not exist"

    with open(JSON_FEED, "r", encoding="utf-8") as f:
        json_data = json.load(f)

    assert len(json_data) >= 1000, f"Expected at least 1,000 items, got {len(json_data)}"

    with open(CSV_FEED, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        csv_rows = list(reader)

    assert len(csv_rows) >= 1000, f"Expected at least 1,000 CSV rows, got {len(csv_rows)}"
    assert len(json_data) == len(csv_rows), "JSON and CSV counts must match"


def test_feed_entries_have_required_fields_and_withheld_ownership():
    """Every record has an id, name, category and item type, with ownership withheld."""
    with open(JSON_FEED, "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data:
        assert item.get("id"), "Item missing id"
        assert item.get("name"), "Item missing name"
        assert item.get("item_type") in ("brand", "product"), f"Item {item['name']} bad item_type"
        assert item.get("category"), f"Item {item['name']} missing category"
        _assert_withheld_record(item)


def test_feed_files_carry_no_withdrawn_fields_or_text():
    """The JSON and CSV feeds have no subterfuge or enrichment field, text, or percentage in any value."""
    with open(JSON_FEED, "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data:
        assert not _withdrawn_keys(item), f"{item['name']} has withdrawn fields"
        for key, value in item.items():
            if key in ("name", "search_aliases"):
                continue
            assert "%" not in json.dumps(value, ensure_ascii=False), f"{item['name']}.{key} has a percentage"

    for path in (JSON_FEED, CSV_FEED):
        text = path.read_text(encoding="utf-8").lower()
        for word in ("subterfuge", "siphon", "surprising", "enrichment", "blackrock", "vanguard", "state street"):
            assert word not in text, f"{path.name} contains {word!r}"

    with open(CSV_FEED, "r", encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert not _withdrawn_keys(header), f"CSV header has withdrawn columns: {header}"


@pytest.mark.parametrize(
    "query",
    [
        "Annie's",
        "Burt's Bees",
        "Ben & Jerry's",
        "Goose Island",
        "Blue Moon",
        "Banfield Pet Hospital",
        "Native Deodorant",
        "Ray-Ban",
        "Rao's",
        "Subway",
        "DeWalt",
        "KitchenAid",
    ],
)
def test_parent_lookup_service_withholds_ownership(query):
    """A known brand resolves to a record whose ownership fields are withheld."""
    match = parent_service.lookup(query)
    assert match is not None, f"Expected lookup result for {query}"
    _assert_withheld_record(match)


def test_api_feed_endpoints():
    """The list, lookup and stats routes return withheld records with no withdrawn fields."""
    client = TestClient(app)

    res = client.get("/v1/feed/parents?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1000
    assert len(data["results"]) == 10
    for rec in data["results"]:
        _assert_withheld_record(rec)

    lookup_res = client.get("/v1/feed/parents/lookup?query=Burt's Bees")
    assert lookup_res.status_code == 200
    lookup_data = lookup_res.json()
    _assert_withheld_record(lookup_data["match"])

    stats_res = client.get("/v1/feed/parents/stats")
    assert stats_res.status_code == 200
    stats_data = stats_res.json()
    assert stats_data["total_items"] >= 1000
    assert not _withdrawn_keys(stats_data)
    assert stats_data["top_parent_conglomerates"] == []
    assert stats_data["ownership_status"] == WITHHELD
    assert stats_data["categories"]


def test_api_parent_filter_matches_nothing():
    """Parent names are withheld, so a parent filter returns no records and does not error."""
    client = TestClient(app)
    res = client.get("/v1/feed/parents?parent=Clorox&limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert data["results"] == []


def test_api_ignores_withdrawn_filter():
    """The subterfuge filter is gone, so the parameter cannot change the results or add fields."""
    client = TestClient(app)
    res = client.get("/v1/feed/parents?is_surprising=true&limit=5")
    assert res.status_code == 200
    data = res.json()
    assert len(data["results"]) == 5
    for rec in data["results"]:
        _assert_withheld_record(rec)


def test_download_json_serves_withheld_feed():
    """The JSON download route serves every record with ownership withheld."""
    client = TestClient(app)
    res = client.get("/v1/feed/parents/download/json")
    assert res.status_code == 200
    assert "brand_parent_feed.json" in res.headers.get("content-disposition", "")
    data = res.json()
    assert len(data) >= 1000
    for rec in data:
        _assert_withheld_record(rec)


def test_download_csv_serves_withheld_feed():
    """The CSV download route has no withdrawn columns and withholds every ownership value."""
    client = TestClient(app)
    res = client.get("/v1/feed/parents/download/csv")
    assert res.status_code == 200
    assert "brand_parent_feed.csv" in res.headers.get("content-disposition", "")
    rows = list(csv.DictReader(res.text.splitlines()))
    assert len(rows) >= 1000
    assert not _withdrawn_keys(rows[0].keys())
    for row in rows:
        for field in OWNERSHIP_FIELDS:
            assert row[field] == ""
        assert row["ownership_status"] == WITHHELD
        assert row["ethical_swap_recommendation"] == WITHHELD


def test_mcp_tools_carry_no_withdrawn_fields():
    """The MCP parent tools return withheld ownership and no withdrawn fields."""
    from mcp.server import lookup_parent_company, get_brand_parent_feed

    res = lookup_parent_company("Burt's Bees")
    assert "error" not in res
    assert not _withdrawn_keys(res)
    for field in OWNERSHIP_FIELDS:
        assert res[field] is None
    assert res["ownership_status"] == WITHHELD

    feed_res = get_brand_parent_feed(query="Oreo", limit=5)
    assert feed_res["count"] > 0
    for item in feed_res["items"]:
        assert not _withdrawn_keys(item)
        assert item["parent_company"] is None
        assert item["ethical_swap"] == WITHHELD

    missing = lookup_parent_company("no-such-brand-zzz")
    assert "error" in missing
