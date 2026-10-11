import csv
from datetime import date, timedelta

import pytest

from pipeline import price_watch, shopify_catalog


@pytest.fixture
def history(tmp_path, monkeypatch):
    path = tmp_path / "price_history.csv"
    monkeypatch.setattr(price_watch, "HISTORY", path)

    def write(prices, pid="p1", end="2026-11-27"):
        end_d = date.fromisoformat(end)
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=price_watch.FIELDS)
            w.writeheader()
            for i, p in enumerate(prices):
                d = end_d - timedelta(days=len(prices) - i)
                w.writerow({"date": d.isoformat(), "product_id": pid, "title": "T", "seller_name": "S",
                            "currency": "USD", "min_price": p, "max_price": p, "any_available": True, "url": ""})
    return write


def test_too_little_history(history):
    history([20, 20, 20])
    assert price_watch.assess_price("p1", 15, today="2026-11-27")["verdict"] == "insufficient_history"


def test_lowest_recorded(history):
    history([20] * 30)
    res = price_watch.assess_price("p1", 15, today="2026-11-27")
    assert res["verdict"] == "lowest_recorded"
    assert res["typical_price_90d"] == 20


def test_raised_then_lowered(history):
    # Usual $20, raised to $30 in November, "discounted" back to $20 on Black Friday
    history([20] * 60 + [30] * 10)
    res = price_watch.assess_price("p1", 20, today="2026-11-27")
    assert res["verdict"] == "raised_then_lowered"


def test_usual_price(history):
    history([20] * 30)
    assert price_watch.assess_price("p1", 20.5, today="2026-11-27")["verdict"] == "usual_price"


def test_summarize_collapses_variants():
    rows = [
        {"product_id": "p", "title": "T", "seller_name": "S", "currency": "USD", "price": 10.0, "available": False, "url": "u"},
        {"product_id": "p", "title": "T", "seller_name": "S", "currency": "USD", "price": 14.0, "available": True, "url": "u"},
    ]
    out = price_watch.summarize(rows)["p"]
    assert (out["min_price"], out["max_price"], out["any_available"]) == (10.0, 14.0, True)


def test_normalize_converts_minor_units():
    product = {"id": "gid://p", "title": "Tee", "rating": {"value": 4.5, "count": 3}}
    variant = {"id": "gid://v", "price": {"amount": 3690, "currency": "USD"}, "availability": {"available": True},
               "seller": {"name": "Fair Indigo", "url": "https://x"}, "url": "https://x/p"}
    row = shopify_catalog.normalize_variant(product, variant)
    assert row["price"] == 36.9
    assert row["seller_name"] == "Fair Indigo"
