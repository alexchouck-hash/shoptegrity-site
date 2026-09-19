"""Parent Company & Product Lookup Service.

Loads the 1,000+ Brand & Product Parent Feed into memory for high-performance
exact, normalized substring, and fuzzy matching.
"""

import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Dict, Any, Optional


FEED_JSON_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "brand_parent_feed.json"


def normalize_string(text: str) -> str:
    """Normalize text for insensitive search."""
    t = text.lower()
    t = re.sub(r"[^\w\s]", "", t)
    return re.sub(r"\s+", " ", t).strip()


class ParentLookupService:
    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or FEED_JSON_PATH
        self._feed: List[Dict[str, Any]] = []
        self._by_id: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        if not self.data_path.exists():
            # Trigger generator if missing
            from pipeline.build_parent_feed import generate_and_export_feed
            self._feed = generate_and_export_feed(json_path=str(self.data_path))
        else:
            with open(self.data_path, "r", encoding="utf-8") as f:
                self._feed = json.load(f)

        self._by_id = {item["id"]: item for item in self._feed}

    @property
    def total_count(self) -> int:
        return len(self._feed)

    def get_feed(
        self,
        q: Optional[str] = None,
        category: Optional[str] = None,
        parent: Optional[str] = None,
        is_surprising: Optional[bool] = None,
        item_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Filter and paginate through the parent feed."""
        results = self._feed

        if category:
            cat_norm = category.lower()
            results = [r for r in results if cat_norm in r.get("category", "").lower()]

        if parent:
            p_norm = parent.lower()
            results = [
                r for r in results
                if p_norm in r.get("parent_company", "").lower() or p_norm in r.get("ultimate_parent", "").lower()
            ]

        if is_surprising is not None:
            results = [r for r in results if r.get("is_surprising_or_subterfuge") == is_surprising]

        if item_type:
            results = [r for r in results if r.get("item_type") == item_type]

        if q:
            norm_q = normalize_string(q)
            q_words = norm_q.split()

            def match_score(item: Dict[str, Any]) -> float:
                name_norm = normalize_string(item["name"])
                # Exact match
                if norm_q == name_norm:
                    return 100.0
                # Starts with query
                if name_norm.startswith(norm_q):
                    return 85.0
                # Substring match in name
                if norm_q in name_norm:
                    return 75.0
                # Check aliases
                for alias in item.get("search_aliases", []):
                    alias_norm = normalize_string(alias)
                    if norm_q in alias_norm:
                        return 70.0
                # Word-level matches
                matched_words = sum(1 for w in q_words if w in name_norm)
                if matched_words > 0:
                    return 40.0 + (matched_words / max(len(q_words), 1)) * 20.0
                # Fuzzy similarity
                ratio = SequenceMatcher(None, norm_q, name_norm).ratio()
                if ratio > 0.65:
                    return ratio * 50.0
                return 0.0

            scored = []
            for item in results:
                s = match_score(item)
                if s > 0:
                    scored.append((s, item))
            scored.sort(key=lambda x: x[0], reverse=True)
            results = [item for _, item in scored]

        total = len(results)
        paginated = results[offset : offset + limit]

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "results": paginated,
        }

    def lookup(self, query: str) -> Optional[Dict[str, Any]]:
        """Find the single closest matching brand or product and return full parentage details."""
        res = self.get_feed(q=query, limit=1)
        if res["results"]:
            return res["results"][0]
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Return high-level summary statistics of the feed."""
        parent_counts: Dict[str, int] = {}
        category_counts: Dict[str, int] = {}
        surprising_count = 0
        products_count = 0
        brands_count = 0

        for r in self._feed:
            p = r.get("parent_company", "Unknown")
            parent_counts[p] = parent_counts.get(p, 0) + 1

            cat = r.get("category", "General")
            category_counts[cat] = category_counts.get(cat, 0) + 1

            if r.get("is_surprising_or_subterfuge"):
                surprising_count += 1
            if r.get("item_type") == "product":
                products_count += 1
            else:
                brands_count += 1

        top_parents = sorted(parent_counts.items(), key=lambda x: x[1], reverse=True)[:15]

        return {
            "total_items": len(self._feed),
            "brands_count": brands_count,
            "products_count": products_count,
            "surprising_subterfuge_count": surprising_count,
            "surprising_subterfuge_pct": round((surprising_count / max(len(self._feed), 1)) * 100, 1),
            "top_parent_conglomerates": [
                {"parent_company": p, "count": c} for p, c in top_parents
            ],
            "categories": category_counts,
        }


# Global singleton instance
parent_service = ParentLookupService()
