"""OSHA pipeline tests against an in-memory fake of the DOL v4 API."""

import fnmatch
import json
import urllib.parse

import pytest

from pipeline import osha_enforcement as osha
from pipeline import provenance

INSPECTIONS = [
    {"activity_nr": 1, "estab_name": "WAL-MART STORES EAST LP", "site_city": "A", "site_state": "AR", "open_date": "2021-03-01T00:00:00", "insp_type": "B", "naics_code": "452311"},
    {"activity_nr": 2, "estab_name": "WALMART #1234", "site_city": "B", "site_state": "TX", "open_date": "2024-06-15", "insp_type": "C", "naics_code": "452311"},
    {"activity_nr": 3, "estab_name": "WAL-MART STORES EAST LP", "site_city": "C", "site_state": "OH", "open_date": "2019-01-01", "insp_type": "B", "naics_code": "452311"},  # outside window
    {"activity_nr": 4, "estab_name": "WALMART TIRE & LUBE EXPRESS LLC", "site_city": "D", "site_state": "FL", "open_date": "2022-01-01", "insp_type": "B", "naics_code": "811198"},  # unrelated business
    {"activity_nr": 5, "estab_name": "SAM'S CLUB #8", "site_city": "E", "site_state": "CA", "open_date": "2025-12-31", "insp_type": "B", "naics_code": "452311"},
]
VIOLATIONS = [
    {"activity_nr": 1, "citation_id": "01001", "delete_flag": None, "viol_type": "S", "current_penalty": "7000", "issuance_date": "2021-04-01", "standard": "19100037"},
    {"activity_nr": 1, "citation_id": "01002", "delete_flag": "X", "viol_type": "S", "current_penalty": "5000", "issuance_date": "2021-04-01", "standard": "19100037"},  # withdrawn
    {"activity_nr": 2, "citation_id": "01001", "delete_flag": "", "viol_type": "R", "current_penalty": 15000.5, "issuance_date": "2024-07-01", "standard": "19100157"},
    {"activity_nr": 2, "citation_id": "02001", "delete_flag": None, "viol_type": "O", "current_penalty": None, "issuance_date": "2024-07-01", "standard": "19040039"},
    {"activity_nr": 3, "citation_id": "01001", "delete_flag": None, "viol_type": "W", "current_penalty": "90000", "issuance_date": "2019-02-01", "standard": "x"},
    {"activity_nr": 4, "citation_id": "01001", "delete_flag": None, "viol_type": "S", "current_penalty": "1000", "issuance_date": "2022-02-01", "standard": "x"},
]
TABLES = {"inspection": INSPECTIONS, "violation": VIOLATIONS}


def _matches(row, cond):
    if "and" in cond:
        return all(_matches(row, c) for c in cond["and"])
    if "or" in cond:
        return any(_matches(row, c) for c in cond["or"])
    val, op, target = row.get(cond["field"]), cond["operator"], cond["value"]
    if op == "like":
        return fnmatch.fnmatchcase(str(val), target.replace("%", "*"))
    if op == "gt":
        return str(val) > str(target)
    if op == "lt":
        return str(val) < str(target)
    if op == "in":
        return str(val) in {str(t) for t in target}
    if op == "eq":
        return str(val) == str(target)
    raise AssertionError(op)


class FakeDOL:
    def __init__(self):
        self.calls = []

    def __call__(self, url):
        self.calls.append(url)
        parsed = urllib.parse.urlparse(url)
        table = parsed.path.split("/")[-2]
        q = urllib.parse.parse_qs(parsed.query)
        assert q["X-API-KEY"] == ["test-key"]
        flt = json.loads(q["filter_object"][0])
        fields = q["fields"][0].split(",")
        rows = [{f: r.get(f) for f in fields} for r in TABLES[table] if _matches(r, flt)]
        offset, limit = int(q["offset"][0]), int(q["limit"][0])
        return {"data": rows[offset:offset + limit]}


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("DOL_API_KEY", "test-key")
    monkeypatch.setattr(osha, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(osha.time, "sleep", lambda s: None)
    monkeypatch.setitem(osha.COMPANIES, "walmart", {
        "owner_match": "Walmart Inc.",
        "include": ["WAL-MART%", "WALMART%", "SAM'S CLUB%"],
        "exclude": [r"TIRE & LUBE"],
    })
    return tmp_path / "osha.json"


def test_refresh_counts_window_excludes_withdrawn_and_unrelated(env):
    fake = FakeDOL()
    data = osha.refresh(["walmart"], http_get=fake, path=env)
    rec = data["walmart"]
    assert rec["inspections"] == 3                     # #3 outside window, #4 excluded
    assert rec["violations"] == 3                      # withdrawn citation not counted
    assert rec["violations_by_type"]["serious"] == 1
    assert rec["violations_by_type"]["repeat"] == 1
    assert rec["violations_by_type"]["other"] == 1
    assert rec["current_penalties_usd"] == 22000.5
    assert rec["inspections_with_citations"] == 2
    assert "WALMART TIRE & LUBE EXPRESS LLC" in rec["excluded_names"]
    assert rec["approved"] is False


def test_pagination_reads_every_page(env, monkeypatch):
    monkeypatch.setattr(osha, "PAGE_SIZE", 1)
    fake = FakeDOL()
    rec = osha.refresh(["walmart"], http_get=fake, path=env)["walmart"]
    assert rec["inspections"] == 3
    assert any("offset=1" in c for c in fake.calls)


def test_refresh_requires_api_key(env, monkeypatch, tmp_path):
    monkeypatch.delenv("DOL_API_KEY")
    monkeypatch.setattr(osha, "ROOT", tmp_path)  # no .env here
    with pytest.raises(SystemExit, match="DOL_API_KEY"):
        osha.refresh(["walmart"], http_get=FakeDOL(), path=env)


def test_approval_resets_when_matched_names_change(env):
    osha.refresh(["walmart"], http_get=FakeDOL(), path=env)
    osha.approve(["walmart"], path=env)
    assert osha.refresh(["walmart"], http_get=FakeDOL(), path=env)["walmart"]["approved"] is True

    INSPECTIONS.append({"activity_nr": 6, "estab_name": "WALMART GROCERY PICKUP", "open_date": "2023-01-01"})
    try:
        assert osha.refresh(["walmart"], http_get=FakeDOL(), path=env)["walmart"]["approved"] is False
    finally:
        INSPECTIONS.pop()


def test_manual_exclude_takes_effect_on_refresh(env):
    osha.refresh(["walmart"], http_get=FakeDOL(), path=env)
    osha.exclude("walmart", "SAM'S CLUB #8", path=env)
    rec = osha.refresh(["walmart"], http_get=FakeDOL(), path=env)["walmart"]
    assert "SAM'S CLUB #8" not in rec["matched_names"]
    assert rec["inspections"] == 2


def test_gate_publishes_only_approved_counts(env, monkeypatch):
    osha.refresh(["walmart"], http_get=FakeDOL(), path=env)
    brand = {"name": "Walmart", "parent_company": "Walmart Inc. (Public: WMT, CIK: 0000104169)",
             "ownership_type": "public", "osha_violations_count": 312, "worker_wages_pct": 10.0,
             "marketing_ads_pct": 5.0, "cogs_supply_pct": 60.0, "data_provenance": "verified_sec_filing"}

    monkeypatch.setitem(provenance._OSHA_CACHE, "data", osha.load_enforcement(env))
    rec = provenance.gate_brand(brand, {})
    assert rec["osha_violations_count"] is None          # unapproved: hand-typed 312 withheld
    assert rec["osha_enforcement"] is None

    osha.approve(["walmart"], path=env)
    monkeypatch.setitem(provenance._OSHA_CACHE, "data", osha.load_enforcement(env))
    rec = provenance.gate_brand(brand, {})
    assert rec["osha_violations_count"] == 3
    src = rec["claim_sources"]["osha_violations_count"]
    assert "3 violations cited in 3 inspections opened 2021-2025" in src["citation"]
    assert src["url"].startswith("https://www.osha.gov/ords/imis/establishment.search?")
    assert "establishment=WAL-MART" in src["url"]
    assert rec["osha_enforcement"]["violations_by_type"]["repeat"] == 1
    assert "matched_names" not in rec["osha_enforcement"]


def test_every_osha_queue_company_has_patterns():
    """Each brand parent that carried a hand-typed OSHA count has a matching config entry."""
    from pipeline.top2000_brands import MAJOR_RETAILERS, ETHICAL_CHAMPIONS, VERIFIED_CORPORATIONS
    owners = {r["parent_company"] for r in MAJOR_RETAILERS + ETHICAL_CHAMPIONS + VERIFIED_CORPORATIONS
              if r.get("osha_violations_count") is not None and "Fairphone" not in r["parent_company"]}
    unmatched = [o for o in owners if not any(c["owner_match"] in o for c in osha.COMPANIES.values())]
    assert unmatched == []
