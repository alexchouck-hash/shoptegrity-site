import json
import re

import pytest
from fastapi.testclient import TestClient
from api.app.main import app

client = TestClient(app)

WITHHELD = "Withheld: no cited source yet"

# Named companies and platforms that must not appear on the housing page or API.
NAMED_PARTIES = [
    r"Invitation Homes", r"Progress Residential", r"Pretium", r"Blackstone", r"Tricon",
    r"Starwood", r"Equity Residential", r"AvalonBay", r"Greystar", r"American Homes 4 Rent",
    r"RealPage", r"Yardi", r"YieldStar", r"Wells Fargo", r"\bChase\b", r"Champlain Housing Trust",
    r"Experian", r"Piñata", r"RentReporters", r"\bBilt\b",
]

# Accusation and conduct words banned when they describe a named party.
BANNED_WORDS = (
    r"\b(disguised|secretly|deceive|deception|predatory|exploitative|co-conspirator|"
    r"conspiracy|cartels?|monopoly|illegal|siphon|camouflage|captive|shell|rigged|theft)\b"
)


def _page_text():
    res = client.get("/housing")
    assert res.status_code == 200
    return res.text


def test_housing_view_loads_successfully():
    """The /housing page renders with its core sections and script hooks."""
    html = _page_text()

    assert "Housing &amp; Rental Integrity Guide" in html or "Housing & Rental Integrity Guide" in html
    assert "Who Actually Owns Where You Live?" in html

    # Demographics: figures are withheld, labels remain
    assert "Single-Family Rentals" in html
    assert "65.6%" not in html
    assert "34.4%" not in html
    assert WITHHELD in html

    # Ownership ladder
    assert "Community Land Trusts (CLTs)" in html
    assert "Mom-and-Pop" in html

    # Illustrative rent split
    assert "The $100 Rent Dollar Illustration" in html
    assert "RENT_SPLIT_DATA" in html
    assert "splitBarLocal" in html
    assert "renderSplitData" in html

    # Landlord questionnaire
    assert "Interactive Landlord Questionnaire" in html
    assert "runLandlordAudit" in html
    assert "auditScoreVal" in html

    # Swaps
    assert "Actionable Housing &amp; Mortgage Swaps" in html or "Actionable Housing & Mortgage Swaps" in html
    assert "Corporate Complex → Local Duplex" in html
    assert "Community Credit Union" in html

    # Responsible renting playbook
    assert "Report Your Rent to Credit Bureaus" in html
    assert "Audit Your Lease for Junk Clauses" in html

    # Pathways to owning
    assert "FHA Mortgage" in html
    assert "House Hacking" in html

    # Calculator
    assert "Interactive Rent vs. Own Equity Simulator" in html
    assert "rentSlider" in html
    assert "updateCalculator" in html
    assert 'id="netAdvantage"' in html


def test_housing_page_names_no_companies():
    """No named company, platform, or conduct accusation appears on the page."""
    html = _page_text()
    for pattern in NAMED_PARTIES:
        assert re.search(pattern, html) is None, f"named party found: {pattern}"
    assert re.search(BANNED_WORDS, html, flags=re.IGNORECASE) is None


def test_housing_page_has_no_unsourced_placeholders():
    """Static placeholder outputs and unsourced program figures are gone."""
    html = _page_text()
    for stale in [
        "$169,450",
        "$74,800",
        "$2,410",
        "+$42,100",
        "Homeownership Advantage",
        "totalRent * 0.35",
        "guaranteed",
        "25%–40%",
        "25%-40%",
        "60%–100%",
        "$1,800–$3,600",
        "$3,000–$8,000",
        "3.5% down",
        "down to 580",
        "Verified",
        "verified",
        "retention rates",
        "Net Wealth Difference",
        "Financial Projection Summary",
    ]:
        assert stale not in html, f"stale text still on page: {stale}"


def test_housing_page_labels_grades_as_opinion():
    """Every rating on the page is labelled as a Shoptegrity opinion."""
    html = _page_text()
    assert html.count("Shoptegrity opinion") >= 7  # six ladder tiers plus the questionnaire result
    # Each score badge sits beside the opinion label
    assert len(re.findall(r"Shoptegrity opinion · Score: \d+/100 · Grade [A-F]", html)) == 6


def test_housing_page_withholds_program_figures():
    """Program figures are withheld and point to agency homepages only."""
    html = _page_text()
    assert html.count(WITHHELD) >= 10
    assert "https://www.hud.gov" in html
    assert "https://www.va.gov" in html
    assert "https://www.usda.gov" in html


def test_base_navigation_includes_housing():
    """Verify that the navigation bar on other pages links to /housing."""
    res = client.get("/")
    assert res.status_code == 200
    assert 'href="/housing"' in res.text
    assert "Housing &amp; Rentals" in res.text or "Housing & Rentals" in res.text


def test_housing_api_overview():
    """The /v1/housing/overview endpoint returns the withheld, structured data."""
    res = client.get("/v1/housing/overview")
    assert res.status_code == 200
    data = res.json()

    # Demographics: every figure is null
    demo = data["demographics"]
    assert demo["status"] == WITHHELD
    for key, value in demo.items():
        if key in ("status", "data_sources"):
            continue
        assert value is None, f"demographic figure not withheld: {key}"

    # Rent splits: illustrative, shares sum to 100
    splits = data["rent_dollar_splits"]
    assert set(splits) == {"tier_1_clt", "tier_3_mom_pop", "tier_6_institutional"}
    for tier in splits.values():
        assert tier["local_retention_pct"] + tier["wall_street_leakage_pct"] == 100
        assert "score" not in tier and "grade" not in tier

    # Ownership ladder: six tiers, each labelled as an opinion, no retention rates
    ladder = data["ownership_ladder"]
    assert len(ladder) == 6
    assert [t["tier"] for t in ladder] == [1, 2, 3, 4, 5, 6]
    assert ladder[0]["score"] == 98 and ladder[0]["grade"] == "A"
    assert ladder[5]["score"] == 16 and ladder[5]["grade"] == "F"
    for tier in ladder:
        assert tier["rating_label"] == "Shoptegrity opinion"
        assert "retention_rate_pct" not in tier
        assert "wall_street_risk" not in tier

    # Mega-landlords: empty until records have cited sources
    assert data["mega_landlords"] == []

    # Swaps: four cards, no dollar figures or percentages in the impact text
    swaps = data["swaps"]
    assert len(swaps) == 4
    for swap in swaps:
        assert not re.search(r"[\d$%]", swap["financial_impact"])

    # Whole payload names no company and uses no banned accusation words
    text = json.dumps(data)
    for pattern in NAMED_PARTIES:
        assert re.search(pattern, text) is None, f"named party in API: {pattern}"
    assert re.search(BANNED_WORDS, text, flags=re.IGNORECASE) is None


def test_housing_api_rent_split_and_landlords():
    """Dedicated sub-endpoints return the illustrative split and the empty registry."""
    res_split = client.get("/v1/housing/rent-split")
    assert res_split.status_code == 200
    body = res_split.json()
    assert "tier_1_clt" in body
    for tier in body.values():
        assert sum(row["cents"] for row in tier["breakdown"]) == 100
        assert "label" in tier

    res_landlords = client.get("/v1/housing/landlords")
    assert res_landlords.status_code == 200
    assert res_landlords.json() == []
