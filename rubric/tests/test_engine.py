import pytest
from rubric.engine import compute_scores, load_rubric

WITHHELD = "Withheld: no cited source yet"


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
        # The co-op default for capital extraction needs its own cited record
        {
            "dimension": "capital_extraction",
            "source_type": "state_registry",
            "fact_text": "Cooperative association owned by its members; no outside shareholders.",
            "source_url": "https://mblsportal.sos.state.mn.us",
        },
    ]
    rubric = load_rubric()
    result = compute_scores(company, evidence, rubric)

    assert result.dimensions["ownership"].value == 92.0
    assert result.dimensions["ownership"].status == "scored"
    assert result.dimensions["capital_extraction"].value == 90.0
    # No cited pay or locality record, so those dimensions are withheld
    assert result.dimensions["pay_equity"].value is None
    assert result.dimensions["pay_equity"].explanation == WITHHELD
    assert result.dimensions["locality"].value is None
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
            "fact_text": "Acquired by a private equity platform.",
            "source_url": "https://example.com/acquisition",
        },
        {
            "dimension": "capital_extraction",
            "source_type": "trade_press",
            "fact_text": "Distributions to the sponsor exceed reinvestment (test fixture).",
            "source_url": "https://example.com/acquisition",
        },
    ]
    rubric = load_rubric()
    result = compute_scores(company, evidence, rubric)

    assert result.dimensions["ownership"].value == 10.0
    assert result.dimensions["capital_extraction"].value == 10.0
    # The pay ratio is present on the record but has no cited pay record, so it is withheld
    assert result.dimensions["pay_equity"].value is None
    assert result.dimensions["pay_equity"].explanation == WITHHELD
    assert result.dimensions["locality"].value is None
    assert result.composite_score is not None
    assert result.composite_score < 40.0


def test_uncited_numbers_never_score():
    company = {
        "id": "uncited-1",
        "name": "Uncited Test Co",
        "ownership_type": "private_equity",
        "locality_tier": "private_equity_rollup",
        "capital_extraction_ratio": 1.2,
        "ceo_pay_ratio": 350.0,
    }
    rubric = load_rubric()
    result = compute_scores(company, [], rubric)

    for key in ("capital_extraction", "pay_equity", "locality", "ownership"):
        assert result.dimensions[key].value is None, key
        assert result.dimensions[key].explanation == WITHHELD, key
    assert result.composite_score is None


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
