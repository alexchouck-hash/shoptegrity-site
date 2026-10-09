"""SEC XBRL financials extractor.

Pulls audited annual figures straight from SEC EDGAR's XBRL "companyfacts" API
so that every dollar figure we attribute to a public company traces back to a
specific filing (accession number + link), instead of being hand-typed.

Usage:
    python -m pipeline.sec_financials            # refresh data/sec_financials.json
    python -m pipeline.sec_financials 0000104169 # refresh specific CIKs

Raw API responses are cached in data/sec_cache/ (gitignored). The compact,
committed output is data/sec_financials.json, which the brand and healthcare
pipelines read offline.
"""

import json
import re
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "sec_cache"
OUTPUT_PATH = ROOT / "data" / "sec_financials.json"

# SEC requires a descriptive User-Agent with contact info for automated access.
USER_AGENT = "Shoptegrity research pipeline research@shopteg.com"

# Concept fallbacks, in order of preference.
REVENUE_CONCEPTS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "RevenuesNetOfInterestExpense",
    "SalesRevenueNet",
]
NET_INCOME_CONCEPTS = ["NetIncomeLoss", "ProfitLoss"]
BUYBACK_CONCEPTS = ["PaymentsForRepurchaseOfCommonStock", "PaymentsForRepurchaseOfEquity"]
DIVIDEND_CONCEPTS = ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends", "PaymentsOfOrdinaryDividends"]


def normalize_cik(cik: str) -> str:
    return re.sub(r"\D", "", cik).zfill(10)


def extract_cik(text: Optional[str]) -> Optional[str]:
    """Pull a CIK out of strings like 'Walmart Inc. (Public: WMT, CIK: 0000104169)'."""
    if not text:
        return None
    m = re.search(r"CIK:\s*(\d{4,10})", text)
    return normalize_cik(m.group(1)) if m else None


def fetch_companyfacts(cik: str, use_cache: bool = True) -> Dict[str, Any]:
    cik = normalize_cik(cik)
    cache_file = CACHE_DIR / f"CIK{cik}.json"
    if use_cache and cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.load(resp)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(data), encoding="utf-8")
    time.sleep(0.15)  # stay well under SEC's 10 req/sec limit
    return data


def _annual_facts(facts: Dict[str, Any], taxonomy: str, concept: str, form_prefix: str = "10-K") -> List[Dict[str, Any]]:
    """Full-year duration facts for a concept, from the given form type."""
    node = facts.get("facts", {}).get(taxonomy, {}).get(concept)
    if not node:
        return []
    out = []
    for f in node.get("units", {}).get("USD", []):
        if not str(f.get("form", "")).startswith(form_prefix):
            continue
        start, end = f.get("start"), f.get("end")
        if not start or not end:
            continue
        days = (date.fromisoformat(end) - date.fromisoformat(start)).days
        if 350 <= days <= 380:
            out.append({**f, "concept": concept})
    return out


def _pick(facts: Dict[str, Any], concepts: List[str], fiscal_end: str) -> Optional[Dict[str, Any]]:
    """Value for the fiscal year ending on fiscal_end; latest-filed wins (captures restatements)."""
    for concept in concepts:
        matches = [f for f in _annual_facts(facts, "us-gaap", concept) if f["end"] == fiscal_end]
        if matches:
            return max(matches, key=lambda f: f.get("filed", ""))
    return None


def _latest_fiscal_end(facts: Dict[str, Any]) -> Optional[str]:
    ends = [f["end"] for c in REVENUE_CONCEPTS for f in _annual_facts(facts, "us-gaap", c)]
    return max(ends) if ends else None


def filing_url(cik: str, accn: str) -> str:
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accn.replace('-', '')}/"


def extract_financials(cik: str, facts: Dict[str, Any]) -> Dict[str, Any]:
    cik = normalize_cik(cik)
    result: Dict[str, Any] = {
        "cik": cik,
        "entity_name": facts.get("entityName"),
        "edgar_url": f"https://www.sec.gov/edgar/browse/?CIK={cik}",
    }
    fiscal_end = _latest_fiscal_end(facts)
    if not fiscal_end:
        result["error"] = "No annual 10-K revenue facts found"
        return result
    result["fiscal_year_end"] = fiscal_end

    figures: Dict[str, Any] = {}
    for key, concepts in [
        ("revenue", REVENUE_CONCEPTS),
        ("net_income", NET_INCOME_CONCEPTS),
        ("buybacks", BUYBACK_CONCEPTS),
        ("dividends", DIVIDEND_CONCEPTS),
    ]:
        f = _pick(facts, concepts, fiscal_end)
        if f:
            figures[key] = {
                "value": f["val"],
                "concept": f"us-gaap:{f['concept']}",
                "accession": f["accn"],
                "form": f["form"],
                "filed": f.get("filed"),
                "url": filing_url(cik, f["accn"]),
            }

    # CEO ("PEO") Summary Compensation Table total, from the proxy's pay-vs-performance XBRL.
    peo = _annual_facts(facts, "ecd", "PeoTotalCompAmt", form_prefix="DEF 14A")
    if peo:
        latest = max(peo, key=lambda f: (f["end"], f.get("filed", "")))
        figures["ceo_total_comp"] = {
            "value": latest["val"],
            "concept": "ecd:PeoTotalCompAmt",
            "fiscal_year_end": latest["end"],
            "accession": latest["accn"],
            "form": latest["form"],
            "filed": latest.get("filed"),
            "url": filing_url(cik, latest["accn"]),
        }

    result["figures"] = figures
    return result


def build_receipt(fin: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Display-ready receipt with percentages derived only from filed values."""
    figs = fin.get("figures") or {}
    rev = (figs.get("revenue") or {}).get("value")
    if not rev:
        return None
    ni = (figs.get("net_income") or {}).get("value")
    buy = (figs.get("buybacks") or {}).get("value")
    div = (figs.get("dividends") or {}).get("value")
    ceo = (figs.get("ceo_total_comp") or {}).get("value")
    payout = (buy or 0) + (div or 0) if (buy is not None or div is not None) else None

    receipt = {
        "cik": fin["cik"],
        "entity_name": fin.get("entity_name"),
        "fiscal_year_end": fin.get("fiscal_year_end"),
        "filing_url": figs["revenue"]["url"],
        "accession": figs["revenue"]["accession"],
        "total_revenue_usd": format_usd(rev),
        "net_income_usd": format_usd(ni) if ni is not None else None,
        "shareholder_dividends_usd": format_usd(div) if div is not None else None,
        "shareholder_buybacks_usd": format_usd(buy) if buy is not None else None,
        "total_shareholder_payout_usd": format_usd(payout) if payout is not None else None,
        "shareholder_payout_pct_of_revenue": round(payout / rev * 100, 2) if payout is not None else None,
        "shareholder_payout_pct_of_net_income": round(payout / ni * 100, 1) if payout is not None and ni and ni > 0 else None,
        "ceo_compensation_usd": format_usd(ceo) if ceo is not None else None,
        "ceo_comp_fiscal_year_end": (figs.get("ceo_total_comp") or {}).get("fiscal_year_end"),
        "ceo_comp_filing_url": (figs.get("ceo_total_comp") or {}).get("url"),
        "ceo_pay_pct_of_revenue": round(ceo / rev * 100, 4) if ceo is not None else None,
        "source_note": "Figures extracted from SEC EDGAR XBRL financial data for the cited filings.",
    }
    return receipt


def format_usd(v: Optional[float]) -> Optional[str]:
    if v is None:
        return None
    a = abs(v)
    sign = "-" if v < 0 else ""
    if a >= 1e9:
        return f"{sign}${a / 1e9:,.2f} Billion"
    if a >= 1e6:
        return f"{sign}${a / 1e6:,.2f} Million"
    return f"{sign}${a:,.0f}"


def load_financials() -> Dict[str, Dict[str, Any]]:
    if not OUTPUT_PATH.exists():
        return {}
    return json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))


def collect_ciks() -> List[str]:
    """Every CIK referenced by the brand and healthcare source records."""
    from pipeline.top2000_brands import VERIFIED_CORPORATIONS, MAJOR_RETAILERS, ETHICAL_CHAMPIONS
    from pipeline.healthcare_2000 import VERIFIED_HEALTHCARE_ENTITIES

    ciks = set()
    for rec in VERIFIED_CORPORATIONS + MAJOR_RETAILERS + ETHICAL_CHAMPIONS:
        c = extract_cik(rec.get("parent_company"))
        if c:
            ciks.add(c)
    for rec in VERIFIED_HEALTHCARE_ENTITIES:
        c = extract_cik(rec.get("parent_organization"))
        if c:
            ciks.add(c)
    return sorted(ciks)


def refresh(ciks: Optional[List[str]] = None, use_cache: bool = False) -> Dict[str, Dict[str, Any]]:
    existing = load_financials()
    targets = [normalize_cik(c) for c in ciks] if ciks else collect_ciks()
    for cik in targets:
        try:
            facts = fetch_companyfacts(cik, use_cache=use_cache)
            existing[cik] = extract_financials(cik, facts)
            print(f"  {cik} {existing[cik].get('entity_name')} FY{existing[cik].get('fiscal_year_end')}")
        except Exception as exc:  # keep going; record the failure so it shows in the queue
            existing[cik] = {"cik": cik, "error": str(exc)}
            print(f"  {cik} ERROR {exc}")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(existing, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {len(existing)} companies to {OUTPUT_PATH}")
    return existing


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    refresh(sys.argv[1:] or None)
