import pytest
from fastapi.testclient import TestClient
from api.app.main import app

client = TestClient(app)


def test_housing_view_loads_successfully():
    """Verify that the /housing page returns HTTP 200 with proper content."""
    res = client.get("/housing")
    assert res.status_code == 200
    html = res.text

    # Core titles and branding
    assert "Housing &amp; Rental Integrity Guide" in html or "Housing & Rental Integrity Guide" in html
    assert "Who Actually Owns Where You Live?" in html

    # Demographics section assertions
    assert "65.6%" in html
    assert "34.4%" in html
    assert "Single-Family Rentals" in html

    # 6-Tier Hierarchy assertions
    assert "Community Land Trusts (CLTs)" in html
    assert "Mom-and-Pop" in html
    assert "Invitation Homes" in html
    assert "Blackstone" in html
    assert "RealPage" in html

    # $100 Rent Cash Flow Split assertions
    assert "The $100 Rent Dollar Cash Flow Split" in html
    assert "RENT_SPLIT_DATA" in html
    assert "splitBarLocal" in html
    assert "renderSplitData" in html

    # Landlord Integrity Auditor assertions
    assert "Interactive Landlord Integrity Auditor" in html
    assert "runLandlordAudit" in html
    assert "auditScoreVal" in html

    # Actionable Housing Swaps assertions
    assert "Actionable Housing &amp; Mortgage Swaps" in html or "Actionable Housing & Mortgage Swaps" in html
    assert "Corporate Complex → Local Duplex" in html or "Corporate Complex" in html
    assert "Community Credit Union" in html

    # Responsible Renting Playbook
    assert "Report Your Rent to Credit Bureaus" in html
    assert "Audit Your Lease for Junk Clauses" in html

    # Pathways to Owning
    assert "FHA Mortgage" in html
    assert "HomeReady" in html
    assert "House Hacking" in html

    # Interactive Calculator
    assert "Interactive Rent vs. Own Equity Simulator" in html
    assert "rentSlider" in html
    assert "updateCalculator" in html


def test_base_navigation_includes_housing():
    """Verify that the navigation bar on other pages links to /housing."""
    res = client.get("/")
    assert res.status_code == 200
    assert 'href="/housing"' in res.text
    assert "Housing &amp; Rentals" in res.text or "Housing & Rentals" in res.text


def test_housing_api_overview():
    """Verify the /v1/housing/overview REST API returns valid structured data."""
    res = client.get("/v1/housing/overview")
    assert res.status_code == 200
    data = res.json()

    # Demographics check
    assert "demographics" in data
    demo = data["demographics"]
    assert demo["homeownership_rate_pct"] == 65.6
    assert demo["renter_rate_pct"] == 34.4
    assert demo["under_35_renter_rate_pct"] == 62.1

    # Rent dollar splits check
    assert "rent_dollar_splits" in data
    splits = data["rent_dollar_splits"]
    assert "tier_1_clt" in splits
    assert splits["tier_1_clt"]["local_retention_pct"] == 100.0
    assert "tier_6_institutional" in splits
    assert splits["tier_6_institutional"]["wall_street_leakage_pct"] == 74.0

    # Ownership ladder check
    assert "ownership_ladder" in data
    ladder = data["ownership_ladder"]
    assert len(ladder) == 6
    assert ladder[0]["tier"] == 1
    assert ladder[0]["score"] == 98
    assert ladder[5]["tier"] == 6
    assert ladder[5]["score"] == 16

    # Mega-landlords check
    assert "mega_landlords" in data
    landlords = data["mega_landlords"]
    assert len(landlords) >= 5
    names = [l["name"] for l in landlords]
    assert any("Invitation Homes" in n for n in names)
    assert any("Progress Residential" in n for n in names)
    assert any("Blackstone" in n for n in names)
    assert any("Greystar" in n for n in names)

    # Swaps check
    assert "swaps" in data
    swaps = data["swaps"]
    assert len(swaps) == 4


def test_housing_api_rent_split_and_landlords():
    """Verify dedicated sub-endpoints for rent splits and mega landlords."""
    res_split = client.get("/v1/housing/rent-split")
    assert res_split.status_code == 200
    assert "tier_1_clt" in res_split.json()

    res_landlords = client.get("/v1/housing/landlords")
    assert res_landlords.status_code == 200
    assert len(res_landlords.json()) >= 5
