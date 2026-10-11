"""Client for Shopify's Global Catalog (UCP over MCP).

Searches products across Shopify merchants without an API key. Shopify fetches
our agent profile (web/static/ucp-agent.json, served at /static/ucp-agent.json)
on every call to decide which catalog fields to return.
"""

import os
from typing import Any, Dict, List, Optional

import httpx

CATALOG_URL = "https://catalog.shopify.com/api/ucp/mcp"
AGENT_PROFILE = os.environ.get("SHOPTEG_UCP_PROFILE", "https://shopteg.com/static/ucp-agent.json")


class CatalogError(RuntimeError):
    pass


def _call(tool: str, arguments: Dict[str, Any], timeout: float = 40.0) -> Dict[str, Any]:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool, "arguments": {"meta": {"ucp-agent": {"profile": AGENT_PROFILE}}, **arguments}},
    }
    res = httpx.post(CATALOG_URL, json=payload, headers={"Accept": "application/json"}, timeout=timeout)
    res.raise_for_status()
    body = res.json()
    if "error" in body:
        raise CatalogError(f"{tool}: {body['error'].get('message')} {body['error'].get('data')}")
    return body["result"]["structuredContent"]


def _money(m: Optional[Dict[str, Any]]) -> Optional[float]:
    # Catalog prices are integers in minor units ({"amount": 3690, "currency": "USD"} is $36.90)
    if not m or m.get("amount") is None:
        return None
    return round(m["amount"] / 100, 2)


def normalize_variant(product: Dict[str, Any], variant: Dict[str, Any]) -> Dict[str, Any]:
    seller = variant.get("seller") or {}
    return {
        "product_id": product.get("id"),
        "variant_id": variant.get("id"),
        "title": product.get("title"),
        "seller_name": seller.get("name"),
        "seller_url": seller.get("url"),
        "price": _money(variant.get("price")),
        "currency": (variant.get("price") or {}).get("currency"),
        "available": (variant.get("availability") or {}).get("available"),
        "url": variant.get("url"),
        "rating": (variant.get("rating") or product.get("rating") or {}).get("value"),
        "rating_count": (variant.get("rating") or product.get("rating") or {}).get("count"),
    }


def search_catalog(query: str, country: str = "US", currency: str = "USD") -> List[Dict[str, Any]]:
    """Search the Global Catalog. Returns one row per product, using its first variant."""
    sc = _call("search_catalog", {"catalog": {"query": query, "context": {"address_country": country, "currency": currency}}})
    rows = []
    for product in sc.get("products", []):
        variants = product.get("variants") or []
        if variants:
            rows.append(normalize_variant(product, variants[0]))
    return rows


def lookup_products(ids: List[str]) -> List[Dict[str, Any]]:
    """Look up 1-50 catalog product IDs. Returns one row per variant."""
    sc = _call("lookup_catalog", {"catalog": {"ids": ids[:50]}})
    return [normalize_variant(p, v) for p in sc.get("products", []) for v in (p.get("variants") or [])]
