from mcp.server import (
    lookup_brand,
    find_alternatives,
    find_local_businesses,
    dollar_split_summary,
    search_top_brands,
    lookup_brand_integrity,
    rate_major_retailers,
    get_retailer_swaps,
)

WITHHELD = "Withheld: no cited source yet"


def test_mcp_lookup():
    res = lookup_brand("Annie")
    assert "Annie's Homegrown" in res["brand"]
    # Parent company is withheld until a cited ownership record exists
    assert res["parent_company"] is None
    assert "composite_score" in res


def test_mcp_alternatives():
    res = find_alternatives("Annie")
    # Swap recommendations are served only after editor approval (none are approved yet)
    assert res["recommended_alternatives"] == []
    assert "Found 0 editor-approved alternatives" in res["summary"]


def test_mcp_local():
    # Minneapolis coordinates
    res = find_local_businesses(44.9778, -93.2650, radius_km=25)
    assert len(res) >= 3
    assert any("Wedge" in b["name"] for b in res)
    # Ownership tiers and flags are withheld until cited
    assert all(b["ownership_tier"] is None for b in res)
    assert all(b["flags"] == [] for b in res)
    assert all(b["verified_locally"] is False for b in res)


def test_mcp_top_brands_search():
    res = search_top_brands(query="Nike", limit=5)
    assert res["total_matches"] >= 1
    assert any("Nike" in b["name"] for b in res["brands"])


def test_mcp_lookup_brand_integrity():
    res = lookup_brand_integrity("Walmart")
    assert res["name"] == "Walmart"
    # Grades are withheld until their inputs are cited
    assert res["grade"] is None
    assert "worker_wages_pct" in res["dollar_flow_split"]
    assert res["dollar_flow_split"]["worker_wages_pct"] is None
    # The shareholder share is derived from the company's SEC filing, so it is published
    assert res["dollar_flow_split"]["basis"]["shareholder_extraction_pct"] == "sec_filing"


def test_mcp_dollar_split_summary_is_withheld():
    res = dollar_split_summary("grocery")
    assert res["category"] == "grocery"
    assert all(p["summary"] == WITHHELD and p["nodes"] is None for p in res["profiles"])


def test_mcp_rate_major_retailers():
    res = rate_major_retailers()
    assert res["count"] >= 7
    names = [r["name"] for r in res["retailers"]]
    assert "Walmart" in names
    assert "Target" in names
    assert "Costco Wholesale" in names
    assert "WinCo Foods" in names


def test_mcp_get_retailer_swaps():
    res = get_retailer_swaps("Home Depot")
    assert res["current_retailer"] == "The Home Depot"
    # Retailer swap recommendations are withheld until cited
    assert res["recommended_swap"] is None


def test_mcp_lookup_parent_company():
    from mcp.server import lookup_parent_company, get_brand_parent_feed

    res = lookup_parent_company("Burt's Bees")
    assert res["parent_company"] is None
    assert res["ownership_status"] == WITHHELD
    assert res["ethical_swap_recommendation"] == WITHHELD

    feed_res = get_brand_parent_feed(query="Oreo", limit=5)
    assert feed_res["total_matches"] >= 1
    assert all(item["parent_company"] is None for item in feed_res["items"])
