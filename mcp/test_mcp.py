from mcp.server import lookup_brand, find_alternatives, find_local_businesses, dollar_split_summary


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
