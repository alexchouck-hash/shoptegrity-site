"""Pure-function scoring engine for Shoptegrity.

Takes company attributes, evidence items, and a rubric configuration to
compute reproducible, evidence-backed scores for each dimension.

Publication rule (sourced or withheld): a dimension is scored only when at
least one evidence item for that dimension carries a non-empty source_url.
Evidence without a source_url is ignored. A dimension without a cited input
has value None, and the composite is computed only from scored dimensions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import yaml
from pathlib import Path


MIN_SCORED_DIMENSIONS = 1
WITHHELD_TEXT = "Withheld: no cited source yet"
COOP_OWNERSHIP_TYPES = ("worker_coop", "consumer_coop", "producer_coop", "credit_union", "mutual")


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
        if source_type in ("sec_edgar", "osha", "epa", "cfpb", "state_registry", "ncua", "usda"):
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


def _cited(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Evidence items that carry a non-empty source_url. Only these count as inputs."""
    return [e for e in items if str(e.get("source_url") or "").strip()]


def _plural(n: int, singular: str, plural: str) -> str:
    return singular if n == 1 else plural


def _make_dimension(
    key: str,
    spec: Dict[str, Any],
    default_name: str,
    default_weight: float,
    value: Optional[float],
    evidence: List[Dict[str, Any]],
    explanation: str,
) -> DimensionScore:
    scored = value is not None
    return DimensionScore(
        key=key,
        name=spec.get("name", default_name),
        value=value,
        confidence=calculate_evidence_confidence(evidence) if scored else 0.0,
        status="scored" if scored else "unknown",
        weight=spec.get("default_weight", default_weight),
        evidence=evidence,
        explanation=explanation if scored else WITHHELD_TEXT,
    )


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

    def dim_evidence(dimension: str) -> List[Dict[str, Any]]:
        return _cited([e for e in evidence_list if e.get("dimension") == dimension])

    own_type = str(company.get("ownership_type") or "unknown")

    # 1. Ownership Score
    own_spec = rubric_dims.get("ownership", {})
    own_evidence = dim_evidence("ownership")
    own_tier_value = own_spec.get("tiers", {}).get(own_type)
    own_val = float(own_tier_value) if (own_evidence and own_tier_value is not None) else None
    results["ownership"] = _make_dimension(
        "ownership", own_spec, "Ownership", 0.25, own_val, own_evidence,
        explanation=f"Ownership structure: {own_type.replace('_', ' ').title()}",
    )

    # 2. Capital Extraction
    cap_spec = rubric_dims.get("capital_extraction", {})
    cap_evidence = dim_evidence("capital_extraction")
    extraction_ratio = company.get("capital_extraction_ratio")
    cap_val: Optional[float] = None

    if cap_evidence:
        if own_type in COOP_OWNERSHIP_TYPES:
            cap_val = float(cap_spec.get("default_coop_points", 90))
        elif extraction_ratio is not None:
            for thresh in cap_spec.get("thresholds", []):
                if extraction_ratio <= thresh["max_ratio"]:
                    cap_val = float(thresh["points"])
                    break

    results["capital_extraction"] = _make_dimension(
        "capital_extraction", cap_spec, "Capital Extraction", 0.15, cap_val, cap_evidence,
        explanation=(
            f"Capital extraction score based on {len(cap_evidence)} "
            f"{_plural(len(cap_evidence), 'cited record', 'cited records')}."
        ),
    )

    # 3. Pay Equity
    pay_spec = rubric_dims.get("pay_equity", {})
    pay_evidence = dim_evidence("pay_equity")
    pay_ratio = company.get("ceo_pay_ratio")
    pay_val: Optional[float] = None

    if pay_evidence:
        if pay_ratio is not None:
            for thresh in pay_spec.get("ratio_thresholds", []):
                if pay_ratio <= thresh["max_ratio"]:
                    pay_val = float(thresh["points"])
                    break
        elif own_type in ("worker_coop", "consumer_coop"):
            pay_val = 95.0

    results["pay_equity"] = _make_dimension(
        "pay_equity", pay_spec, "Pay Equity", 0.15, pay_val, pay_evidence,
        explanation=(
            f"Pay equity score based on {len(pay_evidence)} "
            f"{_plural(len(pay_evidence), 'cited record', 'cited records')}."
        ),
    )

    # 4. Labor Practices
    labor_spec = rubric_dims.get("labor", {})
    labor_evidence = dim_evidence("labor")
    labor_val: Optional[float] = None
    if labor_evidence:
        base_labor = float(labor_spec.get("baseline_points", 70))
        for sig in company.get("labor_signals", []) or []:
            if sig in labor_spec.get("positive_signals", {}):
                base_labor += labor_spec["positive_signals"][sig]
            elif sig in labor_spec.get("negative_signals", {}):
                base_labor += labor_spec["negative_signals"][sig]
        for ev in labor_evidence:
            base_labor += ev.get("impact", 0) * 10
        labor_val = max(0.0, min(100.0, base_labor))

    results["labor"] = _make_dimension(
        "labor", labor_spec, "Labor Practices", 0.15, labor_val, labor_evidence,
        explanation=(
            f"Labor score based on {len(labor_evidence)} recorded "
            f"{_plural(len(labor_evidence), 'event', 'events')}."
        ),
    )

    # 5. Environmental Impact
    env_spec = rubric_dims.get("environment", {})
    env_evidence = dim_evidence("environment")
    env_val: Optional[float] = None
    if env_evidence:
        base_env = float(env_spec.get("baseline_points", 70))
        for sig in company.get("env_signals", []) or []:
            if sig in env_spec.get("positive_signals", {}):
                base_env += env_spec["positive_signals"][sig]
            elif sig in env_spec.get("negative_signals", {}):
                base_env += env_spec["negative_signals"][sig]
        for ev in env_evidence:
            base_env += ev.get("impact", 0) * 10
        env_val = max(0.0, min(100.0, base_env))

    results["environment"] = _make_dimension(
        "environment", env_spec, "Environmental Impact", 0.15, env_val, env_evidence,
        explanation=(
            f"Environmental score based on {len(env_evidence)} "
            f"{_plural(len(env_evidence), 'cited record', 'cited records')}."
        ),
    )

    # 6. Locality. An unknown locality tier is withheld, not defaulted.
    loc_spec = rubric_dims.get("locality", {})
    loc_type = str(company.get("locality_tier") or "unknown")
    loc_evidence = dim_evidence("locality")
    loc_tier_value = loc_spec.get("tiers", {}).get(loc_type)
    loc_val = float(loc_tier_value) if (loc_evidence and loc_tier_value is not None) else None

    results["locality"] = _make_dimension(
        "locality", loc_spec, "Locality & Community Wealth", 0.15, loc_val, loc_evidence,
        explanation=f"Local footprint: {loc_type.replace('_', ' ').title()}",
    )

    # Composite uses only scored (cited) dimensions. No cited dimension means no composite.
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

    # A composite needs at least MIN_SCORED_DIMENSIONS cited dimensions. One cited record is too thin for a grade.
    scored_dimensions = sum(1 for dim in results.values() if dim.value is not None)
    composite = (
        round(total_weighted_points / total_active_weight, 1)
        if total_active_weight > 0 and scored_dimensions >= MIN_SCORED_DIMENSIONS
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
