"""Unit tests for the lead scoring engine (Module 4 / Days 12-14)."""
from __future__ import annotations

import json

import pytest

from sales_intel.ai.scoring.engine import (
    DIMENSIONS,
    composite_score,
    conversion_probability,
    dimension_subscores,
    load_scoring_config,
    score_batch,
    score_lead,
)
from sales_intel.config import WEIGHTS_FILE
from sales_intel.schemas import LeadScore


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------
def test_subscores_cover_all_dimensions_within_range(hot_lead):
    subs = dimension_subscores(hot_lead)
    assert set(subs) == set(DIMENSIONS)
    assert all(0.0 <= v <= 100.0 for v in subs.values())


def test_cold_lead_scores_lower_than_hot_lead(hot_lead, cold_lead, scoring_config):
    hot = score_lead(hot_lead, scoring_config)
    cold = score_lead(cold_lead, scoring_config)
    assert hot.score > cold.score
    assert hot.band == "Hot"
    assert cold.band == "Cold"
    assert hot.conversion_probability > cold.conversion_probability


def test_scores_are_bounded_and_deterministic(hot_lead, scoring_config):
    a = score_lead(hot_lead, scoring_config)
    b = score_lead(hot_lead, scoring_config)
    assert a.score == b.score
    assert 0.0 <= a.score <= 100.0
    assert 0.0 <= a.conversion_probability <= 1.0


def test_response_latency_and_timeline_are_inverted(scoring_config):
    """Lower latency / shorter timeline must score higher, all else equal."""
    from sales_intel.schemas import LeadFeatures

    base = dict(
        lead_id="X", email_opens=5, email_clicks=2, email_replies=1, inbound_replies=1,
        meetings_held=1, call_connect_rate=0.4, industry_match=0.5,
        company_size_score=0.5, seniority_score=0.5, tech_stack_overlap=0.5,
        budget_potential_usd=50_000, pricing_page_visits=3, demo_requests=1,
        content_downloads=2, hiring_signal=1, competitor_mention=1, budget_confirmed=1,
        stakeholders_identified=2, procurement_stage=1, champion_identified=1,
    )
    fast = LeadFeatures(**base, avg_response_latency_hours=2, timeline_months=2)
    slow = LeadFeatures(**base, avg_response_latency_hours=68, timeline_months=14)
    assert score_lead(fast, scoring_config).score > score_lead(slow, scoring_config).score


def test_over_cap_features_are_clamped(cold_lead, scoring_config):
    """Values far above the cap must not push subscores past 100."""
    from sales_intel.schemas import LeadFeatures

    maxed = cold_lead.model_copy(update={
        "email_opens": 10_000, "email_clicks": 10_000, "email_replies": 10_000,
        "inbound_replies": 10_000, "meetings_held": 10_000,
        "call_connect_rate": 1.0, "avg_response_latency_hours": 0.0,
    })
    subs = dimension_subscores(maxed)
    assert subs["engagement"] <= 100.0
    assert subs["engagement"] == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# Composite / probability
# ---------------------------------------------------------------------------
def test_composite_score_is_weighted_mean():
    subs = {"engagement": 100.0, "fit": 0.0, "intent": 0.0, "decision_readiness": 0.0}
    weights = {"engagement": 0.4, "fit": 0.2, "intent": 0.2, "decision_readiness": 0.2}
    assert composite_score(subs, weights) == pytest.approx(40.0)


@pytest.mark.parametrize(
    "score,expected_side",
    [(0.0, "below"), (50.0, "equal"), (100.0, "above")],
)
def test_probability_is_monotonic(score, expected_side):
    p = conversion_probability(score, a=0.11, b=50.0)
    if expected_side == "below":
        assert p < 0.5
    elif expected_side == "equal":
        assert p == pytest.approx(0.5, abs=1e-6)
    else:
        assert p > 0.5


# ---------------------------------------------------------------------------
# Explanations
# ---------------------------------------------------------------------------
def test_drivers_are_sorted_and_contributions_sum_to_score(hot_lead, scoring_config):
    result = score_lead(hot_lead, scoring_config)
    assert len(result.drivers) == 4
    contributions = [d["contribution"] for d in result.drivers]
    assert contributions == sorted(contributions, reverse=True)
    total_share = sum(d["share_of_score_pct"] for d in result.drivers)
    assert total_share == pytest.approx(100.0, abs=0.5)


def test_lead_score_serialises_to_json(hot_lead, scoring_config):
    payload = score_lead(hot_lead, scoring_config).model_dump_json()
    round_trip = LeadScore.model_validate_json(payload)
    assert round_trip.lead_id == "L-HOT"


def test_batch_scoring_preserves_alignment(hot_lead, cold_lead, scoring_config):
    results = score_batch([hot_lead, cold_lead], scoring_config)
    assert [r.lead_id for r in results] == ["L-HOT", "L-COLD"]


# ---------------------------------------------------------------------------
# Config handling
# ---------------------------------------------------------------------------
def test_invalid_weights_are_rejected(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({
        "weights": {"engagement": 0.5, "fit": 0.5, "intent": -0.1, "decision_readiness": 0.1},
    }))
    with pytest.raises(ValueError, match="non-negative"):
        load_scoring_config(bad)


def test_weights_must_sum_to_one(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({
        "weights": {"engagement": 0.5, "fit": 0.5, "intent": 0.5, "decision_readiness": 0.5},
    }))
    with pytest.raises(ValueError, match="sum to 1.0"):
        load_scoring_config(bad)


def test_missing_dimension_is_rejected(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"weights": {"engagement": 1.0}}))
    with pytest.raises(ValueError, match="missing dimensions"):
        load_scoring_config(bad)


def test_tuned_artifact_is_valid_if_present():
    """The Day-14 output must reload through the production path."""
    if not WEIGHTS_FILE.exists():
        pytest.skip("no tuned weights yet — run scripts/tune_weights.py")
    cfg = load_scoring_config()
    assert abs(sum(cfg["weights"].values()) - 1.0) < 1e-6
    assert cfg["model_version"].startswith("m2-scoring")
    assert 0.0 < cfg["logistic_a"] < 1.0
