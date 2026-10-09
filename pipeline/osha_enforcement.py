"""OSHA enforcement pipeline.

Counts OSHA inspections and cited violations for each company in the brand
database, straight from the U.S. Department of Labor's enforcement data
(DOL Open Data Portal API v4, OSHA `inspection` and `violation` tables).

OSHA records name the *establishment* that was inspected ("WAL-MART STORES
EAST LP #1234"), not the parent company, so each company has a list of
establishment-name patterns. Name matching can sweep in unrelated businesses
("TARGET LOGISTICS"), so a company's counts are published only after a person
has reviewed the matched names and approved them. Approval is tied to the exact
set of names: if a refresh matches a new name, the company drops back to
unapproved until it is reviewed again.

Setup:
    1. Get a free API key at https://dataportal.dol.gov/registration
    2. Put it in .env (gitignored) as:  DOL_API_KEY=your-key

Usage:
    python -m pipeline.osha_enforcement refresh [KEY ...]   # pull data (all companies by default)
    python -m pipeline.osha_enforcement review [KEY ...]    # show matched establishment names
    python -m pipeline.osha_enforcement approve KEY [...]   # approve the current name set
    python -m pipeline.osha_enforcement exclude KEY "NAME"  # drop a mismatched establishment name

Raw API pages are cached in data/osha_cache/ (gitignored). The committed output
is data/osha_enforcement.json, which pipeline/provenance.py reads offline.
"""

import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "osha_cache"
OUTPUT_PATH = ROOT / "data" / "osha_enforcement.json"

API_BASE = "https://apiprod.dol.gov/v4/get/OSHA/{table}/json"
PAGE_SIZE = 10000          # API maximum per request
ACTIVITY_CHUNK = 150       # activity numbers per violation query (keeps URLs short)

# Fixed five-calendar-year window so counts are reproducible and comparable.
WINDOW_START = "2021-01-01"
WINDOW_END = "2025-12-31"

INSPECTION_FIELDS = ["activity_nr", "estab_name", "site_city", "site_state", "open_date", "insp_type", "naics_code"]
VIOLATION_FIELDS = ["activity_nr", "citation_id", "delete_flag", "viol_type", "current_penalty", "issuance_date", "standard"]

VIOLATION_TYPES = {"S": "serious", "W": "willful", "R": "repeat", "O": "other", "U": "unclassified"}

# owner_match: substring of the brand record's parent_company.
# include: OSHA LIKE patterns on estab_name (OSHA stores names upper-case).
# exclude: regexes for names the patterns catch but which are a different business.
COMPANIES: Dict[str, Dict[str, Any]] = {
    "walmart": {"owner_match": "Walmart Inc.", "include": ["WAL-MART%", "WALMART%", "WAL MART%", "SAM'S CLUB%", "SAMS CLUB%", "SAM S CLUB%"]},
    "target": {"owner_match": "Target Corporation", "include": ["TARGET CORP%", "TARGET STORE%", "TARGET #%", "TARGET T-%", "TARGET DISTRIBUTION%", "TARGET DC%"]},
    "costco": {"owner_match": "Costco Wholesale", "include": ["COSTCO%"]},
    "amazon": {"owner_match": "Amazon.com Inc.", "include": ["AMAZON.COM%", "AMAZON COM%", "AMAZON FULFILLMENT%", "AMAZON LOGISTICS%", "AMAZON DATA SERVICES%", "WHOLE FOODS MARKET%"]},
    "kroger": {"owner_match": "The Kroger Co.", "include": ["KROGER%", "RALPHS GROCERY%", "FRED MEYER%", "KING SOOPERS%", "SMITH'S FOOD%", "FRY'S FOOD%", "HARRIS TEETER%", "DILLON COMPANIES%", "QUALITY FOOD CENTERS%", "MARIANO'S%", "PICK 'N SAVE%"]},
    "dollar_general": {"owner_match": "Dollar General Corporation", "include": ["DOLLAR GENERAL%", "DOLGENCORP%", "DOLGEN %"]},
    "home_depot": {"owner_match": "The Home Depot", "include": ["HOME DEPOT%", "THE HOME DEPOT%"]},
    "winco": {"owner_match": "WinCo Foods Holdings", "include": ["WINCO FOODS%", "WINCO FOOD%"]},
    "ace_hardware": {"owner_match": "Ace Hardware Corporation", "include": ["ACE HARDWARE CORP%"]},
    "dr_bronners": {"owner_match": "All-One God Faith", "include": ["DR. BRONNER%", "DR BRONNER%", "ALL-ONE GOD FAITH%", "ALL ONE GOD FAITH%"]},
    "king_arthur": {"owner_match": "King Arthur Baking Company", "include": ["KING ARTHUR BAKING%", "KING ARTHUR FLOUR%"]},
    "bobs_red_mill": {"owner_match": "Bob's Red Mill", "include": ["BOB'S RED MILL%", "BOBS RED MILL%", "BOB S RED MILL%"]},
    "equal_exchange": {"owner_match": "Equal Exchange", "include": ["EQUAL EXCHANGE%"]},
    "patagonia": {"owner_match": "Holdfast Collective", "include": ["PATAGONIA INC%", "PATAGONIA, INC%", "PATAGONIA WORKS%", "PATAGONIA RETAIL%"]},
    "organic_valley": {"owner_match": "CROPP Cooperative", "include": ["CROPP COOP%", "CROPP COOPERATIVE%", "ORGANIC VALLEY%"]},
    "unitedhealth": {"owner_match": "UnitedHealth Group", "include": ["UNITEDHEALTH%", "UNITED HEALTHCARE%", "UNITEDHEALTHCARE%", "OPTUM%"]},
    "healthpartners": {"owner_match": "HealthPartners Inc.", "include": ["HEALTHPARTNERS%", "HEALTH PARTNERS INC%"]},
    "kaiser": {"owner_match": "Kaiser Permanente", "include": ["KAISER FOUNDATION%", "KAISER PERMANENTE%"]},
    "hca": {"owner_match": "HCA Healthcare, Inc.", "include": ["HCA HEALTHCARE%", "HCA HEALTH SERVICES%", "HCA - %", "HCA-%"]},
    "plum_health": {"owner_match": "Plum Health Direct Primary Care", "include": ["PLUM HEALTH%"]},
    "cvs": {"owner_match": "CVS Health Corporation", "include": ["CVS PHARMACY%", "CVS HEALTH%", "CVS CAREMARK%", "CVS #%", "CVS STORE%", "AETNA%"]},
    "cigna": {"owner_match": "The Cigna Group", "include": ["CIGNA%", "EXPRESS SCRIPTS%", "EVERNORTH%"]},
    "elevance": {"owner_match": "Elevance Health", "include": ["ELEVANCE HEALTH%", "ANTHEM INSURANCE%", "ANTHEM BLUE CROSS%", "ANTHEM, INC%", "ANTHEM INC%"]},
    "humana": {"owner_match": "Humana Inc.", "include": ["HUMANA%"]},
    "centene": {"owner_match": "Centene Corporation", "include": ["CENTENE%"]},
    "tenet": {"owner_match": "Tenet Healthcare", "include": ["TENET HEALTH%"]},
    "quest": {"owner_match": "Quest Diagnostics", "include": ["QUEST DIAGNOSTICS%"]},
    "aspen_dental": {"owner_match": "TAG - The Aspen Group", "include": ["ASPEN DENTAL%"]},
    "mayo_cleveland": {"owner_match": "Mayo Clinic & Cleveland Clinic", "include": ["MAYO CLINIC%", "CLEVELAND CLINIC%"]},
    "wells_fargo": {"owner_match": "Wells Fargo & Company", "include": ["WELLS FARGO%"]},
    "jpmorgan": {"owner_match": "JPMorgan Chase & Co.", "include": ["JPMORGAN%", "JP MORGAN%", "J.P. MORGAN%", "JPMORGAN CHASE%", "CHASE BANK%"]},
    "bank_of_america": {"owner_match": "Bank of America Corp.", "include": ["BANK OF AMERICA%"]},
    "apple": {"owner_match": "Apple Inc.", "include": ["APPLE INC%", "APPLE, INC%", "APPLE COMPUTER%", "APPLE STORE%", "APPLE RETAIL%"]},
    "procter_gamble": {"owner_match": "Procter & Gamble", "include": ["PROCTER & GAMBLE%", "PROCTER AND GAMBLE%", "THE PROCTER & GAMBLE%", "PROCTER&GAMBLE%"]},
    "general_mills": {"owner_match": "General Mills", "include": ["GENERAL MILLS%"]},
    "nike": {"owner_match": "NIKE, Inc.", "include": ["NIKE INC%", "NIKE, INC%", "NIKE RETAIL%", "NIKE USA%", "NIKE IHM%"]},
}


# ---------------------------------------------------------------------------
# API access
# ---------------------------------------------------------------------------
def load_api_key() -> Optional[str]:
    key = os.environ.get("DOL_API_KEY")
    if key:
        return key.strip()
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*DOL_API_KEY\s*=\s*['\"]?([^'\"\s]+)", line)
            if m:
                return m.group(1)
    return None


def _http_get(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "Shoptegrity research pipeline", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)


def _rows(payload: Any) -> List[Dict[str, Any]]:
    """The API wraps rows as {"data": [...]}; tolerate a bare list too."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for k in ("data", "results", "records"):
            if isinstance(payload.get(k), list):
                return payload[k]
    raise ValueError(f"Unexpected DOL API response shape: {str(payload)[:200]}")


def fetch_all(
    table: str,
    filter_object: Dict[str, Any],
    fields: List[str],
    api_key: str,
    http_get: Callable[[str], Any] = _http_get,
    use_cache: bool = True,
) -> List[Dict[str, Any]]:
    """Page through a DOL v4 table with limit/offset until a short page comes back."""
    out: List[Dict[str, Any]] = []
    offset = 0
    while True:
        params = {
            "limit": PAGE_SIZE,
            "offset": offset,
            "fields": ",".join(fields),
            "filter_object": json.dumps(filter_object, separators=(",", ":")),
        }
        query = urllib.parse.urlencode(params)
        cache_key = hashlib.sha1(f"{table}?{query}".encode()).hexdigest()
        cache_file = CACHE_DIR / f"{table}-{cache_key}.json"
        if use_cache and cache_file.exists():
            page = json.loads(cache_file.read_text(encoding="utf-8"))
        else:
            url = API_BASE.format(table=table) + "?" + query + "&X-API-KEY=" + urllib.parse.quote(api_key)
            page = _rows(http_get(url))
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(page), encoding="utf-8")
            time.sleep(0.2)
        out.extend(page)
        if len(page) < PAGE_SIZE:
            return out
        offset += PAGE_SIZE


def _date_only(v: Any) -> str:
    return str(v or "")[:10]


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
def names_hash(names: Iterable[str]) -> str:
    return hashlib.sha1("\n".join(sorted(set(names))).encode("utf-8")).hexdigest()[:16]


def collect_company(
    key: str,
    cfg: Dict[str, Any],
    api_key: str,
    http_get: Callable[[str], Any] = _http_get,
    use_cache: bool = True,
    manual_excludes: Iterable[str] = (),
) -> Dict[str, Any]:
    excludes = [re.compile(p) for p in cfg.get("exclude", [])]
    manual = {n.upper() for n in manual_excludes}

    inspections: Dict[str, Dict[str, Any]] = {}
    excluded_names: Dict[str, int] = {}
    for pattern in cfg["include"]:
        flt = {"and": [
            {"field": "estab_name", "operator": "like", "value": pattern},
            {"field": "open_date", "operator": "gt", "value": _day_before(WINDOW_START)},
            {"field": "open_date", "operator": "lt", "value": _day_after(WINDOW_END)},
        ]}
        for row in fetch_all("inspection", flt, INSPECTION_FIELDS, api_key, http_get, use_cache):
            name = str(row.get("estab_name", "")).strip().upper()
            opened = _date_only(row.get("open_date"))
            if not (WINDOW_START <= opened <= WINDOW_END):
                continue
            if name in manual or any(rx.search(name) for rx in excludes):
                excluded_names[name] = excluded_names.get(name, 0) + 1
                continue
            inspections[str(row["activity_nr"])] = {**row, "estab_name": name}

    activity_nrs = sorted(inspections)
    violations: List[Dict[str, Any]] = []
    for i in range(0, len(activity_nrs), ACTIVITY_CHUNK):
        chunk = activity_nrs[i:i + ACTIVITY_CHUNK]
        flt = {"field": "activity_nr", "operator": "in", "value": chunk}
        violations.extend(fetch_all("violation", flt, VIOLATION_FIELDS, api_key, http_get, use_cache))

    # Deleted citation items (delete_flag = "X") were withdrawn and do not count.
    live = [v for v in violations if str(v.get("delete_flag") or "").upper() != "X" and str(v.get("activity_nr")) in inspections]

    by_type: Dict[str, int] = {t: 0 for t in VIOLATION_TYPES.values()}
    penalties = 0.0
    cited_activities = set()
    for v in live:
        by_type[VIOLATION_TYPES.get(str(v.get("viol_type") or "U").upper(), "unclassified")] += 1
        try:
            penalties += float(v.get("current_penalty") or 0)
        except (TypeError, ValueError):
            pass
        cited_activities.add(str(v["activity_nr"]))

    matched_names: Dict[str, int] = {}
    for insp in inspections.values():
        matched_names[insp["estab_name"]] = matched_names.get(insp["estab_name"], 0) + 1

    return {
        "key": key,
        "owner_match": cfg["owner_match"],
        "include_patterns": cfg["include"],
        "window_start": WINDOW_START,
        "window_end": WINDOW_END,
        "extracted_at": date.today().isoformat(),
        "inspections": len(inspections),
        "inspections_with_citations": len(cited_activities),
        "violations": len(live),
        "violations_by_type": by_type,
        "current_penalties_usd": round(penalties, 2),
        "matched_names": dict(sorted(matched_names.items(), key=lambda kv: (-kv[1], kv[0]))),
        "excluded_names": dict(sorted(excluded_names.items())),
        "names_hash": names_hash(matched_names),
    }


def _day_before(d: str) -> str:
    return date.fromordinal(date.fromisoformat(d).toordinal() - 1).isoformat()


def _day_after(d: str) -> str:
    return date.fromordinal(date.fromisoformat(d).toordinal() + 1).isoformat()


# ---------------------------------------------------------------------------
# Persistence, review & approval
# ---------------------------------------------------------------------------
def load_enforcement(path: Path = OUTPUT_PATH) -> Dict[str, Dict[str, Any]]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_enforcement(data: Dict[str, Dict[str, Any]], path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def refresh(
    keys: Optional[List[str]] = None,
    http_get: Callable[[str], Any] = _http_get,
    use_cache: bool = False,
    path: Path = OUTPUT_PATH,
) -> Dict[str, Dict[str, Any]]:
    api_key = load_api_key()
    if not api_key:
        raise SystemExit(
            "DOL_API_KEY is not set. Get a free key at https://dataportal.dol.gov/registration "
            "and add DOL_API_KEY=... to .env"
        )
    data = load_enforcement(path)
    for key in keys or list(COMPANIES):
        if key not in COMPANIES:
            raise SystemExit(f"Unknown company key '{key}'. Known: {', '.join(COMPANIES)}")
        prev = data.get(key, {})
        rec = collect_company(key, COMPANIES[key], api_key, http_get, use_cache, prev.get("manual_excludes", []))
        rec["manual_excludes"] = prev.get("manual_excludes", [])
        # Approval survives a refresh only if exactly the same establishment names matched.
        rec["approved"] = bool(prev.get("approved")) and prev.get("approved_names_hash") == rec["names_hash"]
        rec["approved_names_hash"] = prev.get("approved_names_hash") if rec["approved"] else None
        rec["approved_at"] = prev.get("approved_at") if rec["approved"] else None
        data[key] = rec
        state = "approved" if rec["approved"] else "NEEDS REVIEW"
        print(f"  {key:16} {rec['inspections']:5} inspections  {rec['violations']:6} violations  "
              f"{len(rec['matched_names']):4} names  [{state}]")
    save_enforcement(data, path)
    return data


def review(keys: Optional[List[str]] = None, path: Path = OUTPUT_PATH, top: int = 40) -> None:
    data = load_enforcement(path)
    for key in keys or sorted(data):
        rec = data.get(key)
        if not rec:
            print(f"{key}: no data yet (run refresh)")
            continue
        state = "approved" if rec.get("approved") else "NEEDS REVIEW"
        print(f"\n== {key} ({rec['owner_match']}) [{state}] {rec['inspections']} inspections, {rec['violations']} violations")
        for name, n in list(rec["matched_names"].items())[:top]:
            print(f"   {n:5}  {name}")
        if len(rec["matched_names"]) > top:
            print(f"   ... {len(rec['matched_names']) - top} more names")


def approve(keys: List[str], path: Path = OUTPUT_PATH) -> None:
    data = load_enforcement(path)
    for key in keys:
        if key not in data:
            raise SystemExit(f"No data for '{key}'; run refresh first")
        data[key]["approved"] = True
        data[key]["approved_names_hash"] = data[key]["names_hash"]
        data[key]["approved_at"] = date.today().isoformat()
        print(f"Approved {key}: {len(data[key]['matched_names'])} establishment names")
    save_enforcement(data, path)


def exclude(key: str, name: str, path: Path = OUTPUT_PATH) -> None:
    """Record a mismatched establishment name; takes effect on the next refresh."""
    data = load_enforcement(path)
    rec = data.setdefault(key, {})
    rec.setdefault("manual_excludes", [])
    if name.upper() not in rec["manual_excludes"]:
        rec["manual_excludes"].append(name.upper())
    rec["approved"] = False
    save_enforcement(data, path)
    print(f"Excluded '{name.upper()}' from {key}. Re-run: python -m pipeline.osha_enforcement refresh {key}")


# ---------------------------------------------------------------------------
# Publication: used by pipeline/provenance.py
# ---------------------------------------------------------------------------
def establishment_search_url(pattern: str) -> str:
    """OSHA's public establishment search, pre-filled so a reader can check the count."""
    term = pattern.replace("%", "").strip()
    start, end = date.fromisoformat(WINDOW_START), date.fromisoformat(WINDOW_END)
    params = {
        "p_logger": "1", "establishment": term, "State": "all", "officetype": "all", "Office": "all",
        "sitezip": "", "p_case": "all", "p_violations_exist": "all",
        "startmonth": f"{start.month:02d}", "startday": f"{start.day:02d}", "startyear": str(start.year),
        "endmonth": f"{end.month:02d}", "endday": f"{end.day:02d}", "endyear": str(end.year),
    }
    return "https://www.osha.gov/ords/imis/establishment.search?" + urllib.parse.urlencode(params)


def published_record_for(parent_company: Optional[str], data: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Approved enforcement summary for a brand's parent, or None if not publishable."""
    if not parent_company:
        return None
    for rec in data.values():
        if rec.get("owner_match") and rec["owner_match"] in parent_company:
            if rec.get("approved") and rec.get("approved_names_hash") == rec.get("names_hash"):
                return rec
            return None
    return None


def claim_source(rec: Dict[str, Any]) -> Dict[str, str]:
    start_y, end_y = rec["window_start"][:4], rec["window_end"][:4]
    return {
        "citation": (
            f"U.S. Department of Labor OSHA enforcement data: {rec['violations']} violations cited in "
            f"{rec['inspections']} inspections opened {start_y}-{end_y} at establishments named "
            f"{', '.join(p.replace('%', '*') for p in rec['include_patterns'][:4])}"
            f"{' and others' if len(rec['include_patterns']) > 4 else ''} "
            f"(withdrawn citations excluded; extracted {rec['extracted_at']})"
        ),
        "url": establishment_search_url(rec["include_patterns"][0]),
    }


def public_summary(rec: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "window_start": rec["window_start"],
        "window_end": rec["window_end"],
        "inspections": rec["inspections"],
        "inspections_with_citations": rec["inspections_with_citations"],
        "violations": rec["violations"],
        "violations_by_type": rec["violations_by_type"],
        "current_penalties_usd": rec["current_penalties_usd"],
        "establishment_names_matched": len(rec["matched_names"]),
        "extracted_at": rec["extracted_at"],
        "search_url": establishment_search_url(rec["include_patterns"][0]),
    }


def main(argv: List[str]) -> None:
    if not argv or argv[0] not in {"refresh", "review", "approve", "exclude"}:
        print(__doc__)
        return
    cmd, args = argv[0], argv[1:]
    if cmd == "refresh":
        refresh(args or None)
    elif cmd == "review":
        review(args or None)
    elif cmd == "approve":
        if not args:
            raise SystemExit("approve needs at least one company key")
        approve(args)
    elif cmd == "exclude":
        if len(args) != 2:
            raise SystemExit('usage: exclude KEY "ESTABLISHMENT NAME"')
        exclude(args[0], args[1])


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    main(sys.argv[1:])
