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


def test_mcp_lookup():
    res = lookup_brand("Annie")
    assert "Annie's Homegrown" in res["brand"]
    assert res["parent_company"] == "General Mills, Inc."
    assert res["composite_score"] is not None


def test_mcp_alternatives():
    res = find_alternatives("Annie")
    assert len(res["recommended_alternatives"]) >= 1
    assert any("Organic Valley" in a["alternative_brand"] for a in res["recommended_alternatives"])


def test_mcp_local():
    # Minneapolis coordinates
    res = find_local_businesses(44.9778, -93.2650, radius_km=25)
    assert len(res) >= 3
    assert any("Wedge" in b["name"] for b in res)


def test_mcp_top_brands_search():
    res = search_top_brands(query="Nike", limit=5)
    assert res["total_matches"] >= 1
    assert any("Nike" in b["name"] for b in res["brands"])


def test_mcp_lookup_brand_integrity():
    res = lookup_brand_integrity("Walmart")
    assert res["name"] == "Walmart"
    assert res["grade"] == "F"
    assert "worker_wages_pct" in res["dollar_flow_split"]
    assert "shareholder_buybacks_dividends_pct" in res["dollar_flow_split"]
    assert res["dollar_flow_split"]["shareholder_buybacks_dividends_pct"] > res["dollar_flow_split"]["worker_wages_pct"]
    assert "WinCo" in res["recommended_swap"]["swap_name"]


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
    assert "Ace Hardware" in res["recommended_swap"]
