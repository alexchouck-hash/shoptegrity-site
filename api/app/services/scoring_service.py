from typing import Optional, Dict, Any
from rubric.engine import compute_scores, load_rubric, CompanyScoreResult
from api.app.models.core import Entity, Evidence


_rubric_cache = None


def get_cached_rubric():
    global _rubric_cache
    if _rubric_cache is None:
        _rubric_cache = load_rubric()
    return _rubric_cache


def score_entity(entity: Entity, custom_weights: Optional[Dict[str, float]] = None) -> CompanyScoreResult:
    evidence_dicts = [
        {
            "id": ev.id,
            "dimension": ev.dimension,
            "fact_text": ev.fact_text,
            "source_url": ev.source_url,
            "source_name": ev.source_name,
            "source_type": ev.source_type,
            "event_date": ev.event_date,
            "retrieved_at": ev.retrieved_at,
            "impact": ev.impact,
            "status": ev.status,
            "reviewed_by": ev.reviewed_by,
        }
        for ev in entity.evidence_items
        if ev.status == "published"
    ]

    company_dict = {
        "id": entity.id,
        "name": entity.name,
        "ownership_type": entity.ownership_type,
        "locality_tier": entity.locality_tier,
        "ceo_pay_ratio": entity.ceo_pay_ratio,
        "capital_extraction_ratio": entity.capital_extraction_ratio,
        "labor_signals": [],
        "env_signals": [],
    }

    # Extract signals from evidence keywords if available
    for ev in evidence_dicts:
        text_lower = ev["fact_text"].lower()
        if "living wage" in text_lower:
            company_dict["labor_signals"].append("living_wage_certified")
        if "union" in text_lower:
            company_dict["labor_signals"].append("union_represented")
        if "fair trade" in text_lower:
            company_dict["labor_signals"].append("fair_trade_certified")
        if "osha" in text_lower and ev["impact"] < 0:
            company_dict["labor_signals"].append("osha_serious_violation")
        if "nlrb" in text_lower and ev["impact"] < 0:
            company_dict["labor_signals"].append("nlrb_violation")
        if "organic" in text_lower:
            company_dict["env_signals"].append("usda_organic")
        if "regenerative" in text_lower:
            company_dict["env_signals"].append("regenerative_organic")
        if "epa" in text_lower and ev["impact"] < 0:
            company_dict["env_signals"].append("epa_significant_violation")

    rubric = get_cached_rubric()
    return compute_scores(company_dict, evidence_dicts, rubric, custom_weights)
