"""Tests for Brand & Product Parent Company Feed and Lookup API."""

import json
import csv
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from api.app.main import app
from api.app.services.parent_lookup_service import parent_service


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
JSON_FEED = PROJECT_ROOT / "data" / "brand_parent_feed.json"
CSV_FEED = PROJECT_ROOT / "data" / "brand_parent_feed.csv"


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


def test_feed_entries_have_required_fields():
    """Verify all entries contain valid non-empty fields."""
    with open(JSON_FEED, "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data:
        assert item.get("id"), "Item missing id"
        assert item.get("name"), "Item missing name"
        assert item.get("parent_company"), f"Item {item['name']} missing parent_company"
        assert item.get("ultimate_parent"), f"Item {item['name']} missing ultimate_parent"
        assert item.get("ownership_type"), f"Item {item['name']} missing ownership_type"
        assert item.get("category"), f"Item {item['name']} missing category"
        assert isinstance(item.get("is_surprising_or_subterfuge"), bool)
        assert item.get("top_10_percent_enrichment_pct") is not None


@pytest.mark.parametrize(
    "query, expected_parent",
    [
        ("Annie's", "General Mills"),
        ("Burt's Bees", "The Clorox Company"),
        ("Ben & Jerry's", "Unilever"),
        ("Tom's of Maine", "Colgate-Palmolive"),
        ("Goose Island", "Anheuser-Busch InBev"),
        ("Blue Moon", "Molson Coors"),
        ("Banfield Pet Hospital", "Mars, Inc."),
        ("VCA Animal Hospital", "Mars, Inc."),
        ("Native Deodorant", "Procter & Gamble"),
        ("Ray-Ban", "EssilorLuxottica"),
        ("Rao's", "Campbell Soup Company"),
        ("Subway", "Roark Capital"),
        ("DeWalt", "Stanley Black & Decker"),
        ("KitchenAid", "Whirlpool Corporation"),
    ],
)
def test_parent_lookup_service_known_subterfuge_brands(query, expected_parent):
    """Verify that consumer brands with hidden roots accurately map to their true corporate parents."""
    match = parent_service.lookup(query)
    assert match is not None, f"Expected lookup result for {query}"
    assert expected_parent.lower() in match["parent_company"].lower() or expected_parent.lower() in match["ultimate_parent"].lower(), (
        f"For {query}, expected parent {expected_parent}, got {match['parent_company']}"
    )


def test_api_feed_endpoints():
    """Test the FastAPI REST API feed routes."""
    client = TestClient(app)

    # 1. Test get feed list
    res = client.get("/v1/feed/parents?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1000
    assert len(data["results"]) == 10

    # 2. Test lookup endpoint
    lookup_res = client.get("/v1/feed/parents/lookup?query=Burt's Bees")
    assert lookup_res.status_code == 200
    lookup_data = lookup_res.json()
    assert lookup_data["match"]["parent_company"] == "The Clorox Company"
    assert lookup_data["match"]["is_surprising_or_subterfuge"] is True

    # 3. Test stats endpoint
    stats_res = client.get("/v1/feed/parents/stats")
    assert stats_res.status_code == 200
    stats_data = stats_res.json()
    assert stats_data["total_items"] >= 1000
    assert stats_data["surprising_subterfuge_count"] > 0
    assert len(stats_data["top_parent_conglomerates"]) > 0
