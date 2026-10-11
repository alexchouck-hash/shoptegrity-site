"""Daily price recorder for the Shopify Global Catalog, and fake-markdown checks.

Shopify's catalog gives today's price but no "was" price, so a markdown can only
be judged against prices we recorded ourselves. Each run:
  1. searches every query in data/price_watch_queries.txt and adds new product IDs
     to data/price_watch_ids.txt (up to PER_QUERY products per query), then
  2. looks up every watched ID and appends one row per product to
     data/price_history.csv (date, lowest and highest variant price, availability).

Run daily:  python -m pipeline.price_watch
"""

import csv
import statistics
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from pipeline import shopify_catalog

DATA = Path(__file__).resolve().parent.parent / "data"
QUERIES = DATA / "price_watch_queries.txt"
IDS = DATA / "price_watch_ids.txt"
HISTORY = DATA / "price_history.csv"
FIELDS = ["date", "product_id", "title", "seller_name", "currency", "min_price", "max_price", "any_available", "url"]
PER_QUERY = 10
MIN_DAYS = 7


def _read_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]


def discover() -> int:
    known = _read_lines(IDS)
    seen = set(known)
    added = []
    for query in _read_lines(QUERIES):
        try:
            rows = shopify_catalog.search_catalog(query)
        except Exception as exc:  # one failed query should not stop the run
            print(f"search failed for {query!r}: {exc}")
            continue
        for row in rows[:PER_QUERY]:
            if row["product_id"] and row["product_id"] not in seen:
                seen.add(row["product_id"])
                added.append(row["product_id"])
    if added:
        IDS.write_text("\n".join(known + added) + "\n", encoding="utf-8")
    return len(added)


def summarize(variants: List[Dict]) -> Dict[str, Dict]:
    """Collapse variant rows into one row per product."""
    out: Dict[str, Dict] = {}
    for v in variants:
        if v["price"] is None:
            continue
        p = out.setdefault(v["product_id"], {
            "product_id": v["product_id"], "title": v["title"], "seller_name": v["seller_name"],
            "currency": v["currency"], "min_price": v["price"], "max_price": v["price"],
            "any_available": False, "url": v["url"],
        })
        p["min_price"] = min(p["min_price"], v["price"])
        p["max_price"] = max(p["max_price"], v["price"])
        p["any_available"] = p["any_available"] or bool(v["available"])
    return out


def record(today: Optional[str] = None) -> int:
    today = today or date.today().isoformat()
    ids = _read_lines(IDS)
    already = {(r["date"], r["product_id"]) for r in load_history()}
    rows = []
    for i in range(0, len(ids), 50):
        try:
            variants = shopify_catalog.lookup_products(ids[i:i + 50])
        except Exception as exc:
            print(f"lookup failed for batch {i // 50}: {exc}")
            continue
        for prod in summarize(variants).values():
            if (today, prod["product_id"]) not in already:
                rows.append({"date": today, **prod})
    new_file = not HISTORY.exists()
    with HISTORY.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        w.writerows(rows)
    return len(rows)


def load_history(product_id: Optional[str] = None) -> List[Dict]:
    if not HISTORY.exists():
        return []
    with HISTORY.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if product_id is None or r["product_id"] == product_id]


def assess_price(product_id: str, current_price: Optional[float] = None, today: Optional[str] = None) -> Dict:
    """Compare today's price with the prices we recorded.

    Findings describe our own dated observations only. They are not a claim about
    what a seller intended, and they say so.
    """
    rows = sorted(load_history(product_id), key=lambda r: r["date"])
    today_d = datetime.fromisoformat(today).date() if today else date.today()
    prior = [r for r in rows if r["date"] < today_d.isoformat()]
    if current_price is None and rows:
        current_price = float(rows[-1]["min_price"])
    result = {
        "product_id": product_id,
        "current_price": current_price,
        "days_recorded": len({r["date"] for r in prior}),
        "first_recorded": prior[0]["date"] if prior else None,
        "basis": "Lowest variant price recorded by Shoptegrity from Shopify's Global Catalog, once per day.",
    }
    if current_price is None or len({r["date"] for r in prior}) < MIN_DAYS:
        result.update(verdict="insufficient_history",
                      summary=f"Fewer than {MIN_DAYS} days of recorded prices, so we can't judge this price yet.")
        return result

    def window(days: int) -> List[float]:
        start = (today_d - timedelta(days=days)).isoformat()
        return [float(r["min_price"]) for r in prior if r["date"] >= start]

    last90 = window(90) or [float(r["min_price"]) for r in prior]
    last30 = window(30) or last90
    typical = statistics.median(last90)
    lowest = min(last90)
    peak30 = max(last30)
    result.update(typical_price_90d=typical, lowest_price_90d=lowest, highest_price_30d=peak30)

    if peak30 > typical * 1.15 and current_price >= typical * 0.97:
        verdict = "raised_then_lowered"
        summary = (f"We recorded a rise to {peak30:.2f} in the last 30 days. Today's {current_price:.2f} is about "
                   f"the same as the usual {typical:.2f}, so any discount is measured from the raised price.")
    elif current_price <= lowest:
        verdict = "lowest_recorded"
        summary = f"{current_price:.2f} is the lowest price we've recorded (usual price {typical:.2f})."
    elif current_price < typical * 0.95:
        verdict = "below_usual"
        summary = f"{current_price:.2f} is {100 * (1 - current_price / typical):.0f}% below the usual {typical:.2f}."
    elif current_price > typical * 1.05:
        verdict = "above_usual"
        summary = f"{current_price:.2f} is above the usual {typical:.2f}."
    else:
        verdict = "usual_price"
        summary = f"{current_price:.2f} is about the usual price ({typical:.2f})."
    result.update(verdict=verdict, summary=summary)
    return result


if __name__ == "__main__":
    print(f"Discovered {discover()} new products")
    print(f"Recorded {record()} prices to {HISTORY}")
