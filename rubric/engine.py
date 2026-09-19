"""Pure-function scoring engine for Shoptegrity.

Takes company attributes, evidence items, and a rubric configuration to
compute reproducible, evidence-backed scores for each dimension.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import yaml
from pathlib import Path


@dataclass
class DimensionScore:
    key: str
    name: str
    value: Optional[float]
    confidence: float
    status: str  # "scored" | "unknown"
    weight: float
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    explanation: str = ""


@dataclass
class CompanyScoreResult:
    company_id: str
    company_name: str
    rubric_version: str
    computed_at: str
    dimensions: Dict[str, DimensionScore]
    composite_score: Optional[float]
    confidence: float


def load_rubric(rubric_path: Optional[str] = None) -> dict:
    if rubric_path is None:
        rubric_path = str(Path(__file__).parent / "v1.yaml")
    with open(rubric_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def calculate_evidence_confidence(evidence_items: List[Dict[str, Any]]) -> float:
    """Computes confidence score from 0.0 to 1.0 based on evidence quality and freshness."""
    if not evidence_items:
        return 0.2  # baseline minimal confidence when inferred without explicit evidence

    base_score = 0.0
    for item in evidence_items:
        source_type = item.get("source_type", "manual")
        # Reliable official datasets provide highest confidence
        if source_type in ("sec_edgar", "osha", "epa", "state_registry", "ncua", "usda"):
            base_score += 0.35
        elif source_type in ("wikidata", "gleif", "b_corp", "certifier"):
            base_score += 0.25
        elif source_type in ("trade_press", "news", "investigative"):
            base_score += 0.15
        else:
            base_score += 0.10

    # Cap raw source score
    confidence = min(0.95, base_score)
    return round(confidence, 2)


def compute_scores(
    company: Dict[str, Any],
    evidence_list: List[Dict[str, Any]],
    rubric: Optional[Dict[str, Any]] = None,
    custom_weights: Optional[Dict[str, float]] = None,
) -> CompanyScoreResult:
    if rubric is None:
        rubric = load_rubric()

    rubric_dims = rubric.get("dimensions", {})
    results: Dict[str, DimensionScore] = {}

    # 1. Ownership Score
    own_spec = rubric_dims.get("ownership", {})
    own_type = company.get("ownership_type", "unknown")
    own_tiers = own_spec.get("tiers", {})
    own_val = own_tiers.get(own_type)
    own_evidence = [e for e in evidence_list if e.get("dimension") == "ownership"]

    results["ownership"] = DimensionScore(
        key="ownership",
        name=own_spec.get("name", "Ownership"),
        value=float(own_val) if own_val is not None else None,
        confidence=calculate_evidence_confidence(own_evidence) if own_val is not None else 0.0,
        status="scored" if own_val is not None else "unknown",
        weight=own_spec.get("default_weight", 0.25),
        evidence=own_evidence,
        explanation=f"Ownership structure: {own_type.replace('_', ' ').title()}",
    )

    # 2. Capital Extraction
    cap_spec = rubric_dims.get("capital_extraction", {})
    cap_evidence = [e for e in evidence_list if e.get("dimension") == "capital_extraction"]
    extraction_ratio = company.get("capital_extraction_ratio")
    cap_val: Optional[float] = None

    if own_type in ("worker_coop", "consumer_coop", "producer_coop", "credit_union", "mutual"):
        cap_val = float(cap_spec.get("default_coop_points", 90))
        cap_explanation = "Member-owned/Cooperative structure retains or returns capital to members."
    elif extraction_ratio is not None:
        for thresh in cap_spec.get("thresholds", []):
            if extraction_ratio <= thresh["max_ratio"]:
                cap_val = float(thresh["points"])
                break
        cap_explanation = f"Estimated {round(extraction_ratio * 100, 1)}% of profit extracted to buybacks and dividends."
    else:
        cap_explanation = "No public SEC filing or capital extraction disclosures available."

    results["capital_extraction"] = DimensionScore(
        key="capital_extraction",
        name=cap_spec.get("name", "Capital Extraction"),
        value=cap_val,
        confidence=calculate_evidence_confidence(cap_evidence) if cap_val is not None else 0.0,
        status="scored" if cap_val is not None else "unknown",
        weight=cap_spec.get("default_weight", 0.15),
        evidence=cap_evidence,
        explanation=cap_explanation,
    )

    # 3. Pay Equity
    pay_spec = rubric_dims.get("pay_equity", {})
    pay_evidence = [e for e in evidence_list if e.get("dimension") == "pay_equity"]
    pay_ratio = company.get("ceo_pay_ratio")
    pay_val: Optional[float] = None

    if pay_ratio is not None:
        for thresh in pay_spec.get("ratio_thresholds", []):
            if pay_ratio <= thresh["max_ratio"]:
                pay_val = float(thresh["points"])
                break
        pay_explanation = f"CEO-to-median-worker compensation ratio is {int(pay_ratio)}:1."
    elif own_type in ("worker_coop", "consumer_coop"):
        pay_val = 95.0
        pay_explanation = "Cooperative governance enforces capped executive compensation ratios."
    else:
        pay_explanation = "Pay ratio unknown; private company with no required proxy disclosure."

    results["pay_equity"] = DimensionScore(
        key="pay_equity",
        name=pay_spec.get("name", "Pay Equity"),
        value=pay_val,
        confidence=calculate_evidence_confidence(pay_evidence) if pay_val is not None else 0.0,
        status="scored" if pay_val is not None else "unknown",
        weight=pay_spec.get("default_weight", 0.15),
        evidence=pay_evidence,
        explanation=pay_explanation,
    )

    # 4. Labor Practices
    labor_spec = rubric_dims.get("labor", {})
    labor_evidence = [e for e in evidence_list if e.get("dimension") == "labor"]
    base_labor = float(labor_spec.get("baseline_points", 70))
    labor_signals = company.get("labor_signals", [])

    for sig in labor_signals:
        if sig in labor_spec.get("positive_signals", {}):
            base_labor += labor_spec["positive_signals"][sig]
        elif sig in labor_spec.get("negative_signals", {}):
            base_labor += labor_spec["negative_signals"][sig]

    for ev in labor_evidence:
        impact = ev.get("impact", 0)
        base_labor += impact * 10

    labor_val = max(0.0, min(100.0, base_labor))
    results["labor"] = DimensionScore(
        key="labor",
        name=labor_spec.get("name", "Labor Practices"),
        value=labor_val,
        confidence=calculate_evidence_confidence(labor_evidence),
        status="scored",
        weight=labor_spec.get("default_weight", 0.15),
        evidence=labor_evidence,
        explanation=f"Labor score based on {len(labor_evidence)} recorded events and certifications.",
    )

    # 5. Environmental Impact
    env_spec = rubric_dims.get("environment", {})
    env_evidence = [e for e in evidence_list if e.get("dimension") == "environment"]
    base_env = float(env_spec.get("baseline_points", 70))
    env_signals = company.get("env_signals", [])

    for sig in env_signals:
        if sig in env_spec.get("positive_signals", {}):
            base_env += env_spec["positive_signals"][sig]
        elif sig in env_spec.get("negative_signals", {}):
            base_env += env_spec["negative_signals"][sig]

    for ev in env_evidence:
        impact = ev.get("impact", 0)
        base_env += impact * 10

    env_val = max(0.0, min(100.0, base_env))
    results["environment"] = DimensionScore(
        key="environment",
        name=env_spec.get("name", "Environmental Impact"),
        value=env_val,
        confidence=calculate_evidence_confidence(env_evidence),
        status="scored",
        weight=env_spec.get("default_weight", 0.15),
        evidence=env_evidence,
        explanation=f"Environmental score reflects compliance, agricultural practices, and impact records.",
    )

    # 6. Locality
    loc_spec = rubric_dims.get("locality", {})
    loc_type = company.get("locality_tier", "national_public")
    loc_val = loc_spec.get("tiers", {}).get(loc_type, 30)
    loc_evidence = [e for e in evidence_list if e.get("dimension") == "locality"]

    results["locality"] = DimensionScore(
        key="locality",
        name=loc_spec.get("name", "Locality & Community Wealth"),
        value=float(loc_val) if loc_val is not None else None,
        confidence=calculate_evidence_confidence(loc_evidence),
        status="scored" if loc_val is not None else "unknown",
        weight=loc_spec.get("default_weight", 0.15),
        evidence=loc_evidence,
        explanation=f"Local footprint: {loc_type.replace('_', ' ').title()}",
    )

    # Compute composite score
    weights = custom_weights or {k: v.weight for k, v in results.items()}
    total_weighted_points = 0.0
    total_active_weight = 0.0
    conf_sum = 0.0

    for key, dim in results.items():
        w = weights.get(key, dim.weight)
        conf_sum += dim.confidence
        if dim.value is not None:
            total_weighted_points += dim.value * w
            total_active_weight += w

    composite = (
        round(total_weighted_points / total_active_weight, 1)
        if total_active_weight > 0
        else None
    )
    avg_confidence = round(conf_sum / len(results), 2) if results else 0.0

    return CompanyScoreResult(
        company_id=str(company.get("id", "")),
        company_name=str(company.get("name", "")),
        rubric_version=rubric.get("version", "1.0.0"),
        computed_at=datetime.now(timezone.utc).isoformat(),
        dimensions=results,
        composite_score=composite,
        confidence=avg_confidence,
    )
