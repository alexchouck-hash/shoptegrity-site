import pytest
from rubric.engine import compute_scores, load_rubric


def test_coop_scoring():
    company = {
        "id": "coop-1",
        "name": "Wedge Community Co-op",
        "ownership_type": "consumer_coop",
        "locality_tier": "owner_operated_local",
        "labor_signals": ["living_wage_certified", "union_represented"],
        "env_signals": ["usda_organic", "zero_waste_packaging"],
    }
    evidence = [
        {
            "dimension": "ownership",
            "source_type": "state_registry",
            "fact_text": "Incorporated as a Minnesota cooperative association.",
            "source_url": "https://mblsportal.sos.state.mn.us",
        },
        {
            "dimension": "labor",
            "source_type": "certifier",
            "fact_text": "Certified living wage employer by regional coalition.",
            "source_url": "https://example.org/wage",
        },
    ]
    rubric = load_rubric()
    result = compute_scores(company, evidence, rubric)

    assert result.dimensions["ownership"].value == 92.0
    assert result.dimensions["ownership"].status == "scored"
    assert result.dimensions["capital_extraction"].value == 90.0
    assert result.dimensions["pay_equity"].value == 95.0
    assert result.dimensions["locality"].value == 95.0
    assert result.composite_score is not None
    assert result.composite_score > 85.0


def test_private_equity_rollup_scoring():
    company = {
        "id": "pe-1",
        "name": "Acquired Local Plumbing",
        "ownership_type": "private_equity",
        "locality_tier": "private_equity_rollup",
        "capital_extraction_ratio": 1.2,
        "ceo_pay_ratio": 350.0,
        "labor_signals": ["osha_serious_violation"],
        "env_signals": [],
    }
    evidence = [
        {
            "dimension": "ownership",
            "source_type": "trade_press",
            "fact_text": "Acquired by Apex Service Partners (private equity platform).",
            "source_url": "https://example.com/acquisition",
        }
    ]
    rubric = load_rubric()
    result = compute_scores(company, evidence, rubric)

    assert result.dimensions["ownership"].value == 10.0
    assert result.dimensions["capital_extraction"].value == 10.0
    assert result.dimensions["pay_equity"].value == 15.0
    assert result.dimensions["locality"].value == 10.0
    assert result.composite_score is not None
    assert result.composite_score < 40.0


def test_unknown_private_company():
    company = {
        "id": "priv-1",
        "name": "Opaque Holdings LLC",
        "ownership_type": "national_private",
        "locality_tier": "national_private",
        # no extraction ratio, no pay ratio
    }
    rubric = load_rubric()
    result = compute_scores(company, [], rubric)

    assert result.dimensions["capital_extraction"].status == "unknown"
    assert result.dimensions["capital_extraction"].value is None
    assert result.dimensions["pay_equity"].status == "unknown"
    assert result.dimensions["pay_equity"].value is None
