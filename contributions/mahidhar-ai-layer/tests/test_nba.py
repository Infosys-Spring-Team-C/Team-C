"""Tests for the Day-15 next-best-action engine."""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from sales_intel.ai.nba.engine import recommend, recommend_batch
from sales_intel.schemas import InteractionHistory, LeadContext

TODAY = date(2026, 11, 5)


def _ctx(lead_id="L-HOT", **over) -> LeadContext:
    base = dict(
        lead_id=lead_id,
        company_name="Vertex Manufacturing Group",
        industry="Manufacturing",
        lifecycle_stage="qualified",
        seniority="vp",
        decision_maker=True,
        deal_value_usd=85_000,
        last_contact_at=datetime(2026, 10, 31, 10, 0),
        local_hour=11,
        pain_points=["manual lead qualification"],
    )
    base.update(over)
    return LeadContext(**base)


# ---------------------------------------------------------------------------
# Core output contract
# ---------------------------------------------------------------------------
def test_recommendation_has_all_sections(hot_lead, scoring_config):
    nba = recommend(hot_lead, _ctx(), today=TODAY, scoring_config=scoring_config)
    assert nba.priority in {"P0", "P1", "P2", "P3"}
    assert nba.recommended_channel in {"email", "call", "linkedin", "whatsapp", "meeting"}
    assert nba.next_touch_date >= TODAY
    assert nba.cadence and all(t.planned_at >= TODAY for t in nba.cadence)
    assert nba.channel_mix and sum(c.share for c in nba.channel_mix) == 100
    assert nba.content.content_type
    assert nba.content.call_to_action.endswith(("?", "."))
    assert nba.rationale, "every recommendation must be explainable"


def test_next_touch_is_never_in_the_past_or_on_a_weekend(hot_lead, scoring_config):
    nba = recommend(hot_lead, _ctx(), today=TODAY, scoring_config=scoring_config)
    assert nba.next_touch_date >= TODAY
    assert nba.next_touch_date.weekday() != 6, "Sunday is excluded"


def test_primary_channel_leads_the_channel_mix(hot_lead, scoring_config):
    nba = recommend(hot_lead, _ctx(), today=TODAY, scoring_config=scoring_config)
    assert nba.channel_mix[0].channel == nba.recommended_channel
    assert nba.channel_mix[0].share == max(c.share for c in nba.channel_mix)


# ---------------------------------------------------------------------------
# Priority logic
# ---------------------------------------------------------------------------
def test_hot_high_value_lead_outranks_cold_low_value(hot_lead, cold_lead, scoring_config):
    hot = recommend(hot_lead, _ctx(), today=TODAY, scoring_config=scoring_config)
    cold = recommend(
        cold_lead,
        _ctx(lead_id="L-COLD", lifecycle_stage="new", seniority="manager",
             decision_maker=False, deal_value_usd=3_000, last_contact_at=None,
             pain_points=[]),
        today=TODAY, scoring_config=scoring_config,
    )
    assert hot.priority_score > cold.priority_score
    assert hot.priority == "P0"


def test_stale_lead_accumulates_risk_flag(hot_lead, scoring_config):
    nba = recommend(
        hot_lead,
        _ctx(last_contact_at=datetime(2026, 9, 20, 10, 0)),  # 46 days ago
        today=TODAY, scoring_config=scoring_config,
    )
    assert nba.days_since_last_contact > 14
    assert any("stale" in f for f in nba.risk_flags)
    assert any("decays priority" in r for r in nba.rationale)


def test_negotiation_stage_gets_promoted(hot_lead, scoring_config):
    qualified = recommend(hot_lead, _ctx(lifecycle_stage="qualified"), today=TODAY, scoring_config=scoring_config)
    negotiation = recommend(hot_lead, _ctx(lifecycle_stage="negotiation"), today=TODAY, scoring_config=scoring_config)
    assert negotiation.priority_score > qualified.priority_score


# ---------------------------------------------------------------------------
# Guardrails (must never spam)
# ---------------------------------------------------------------------------
def test_do_not_contact_is_suppressed(hot_lead, scoring_config):
    nba = recommend(hot_lead, _ctx(do_not_contact=True), today=TODAY, scoring_config=scoring_config)
    assert nba.suppress is True
    assert "do-not-contact" in (nba.suppress_reason or "")


def test_frequency_cap_is_enforced(hot_lead, scoring_config):
    recent = [
        InteractionHistory(channel="email", occurred_at=datetime(2026, 11, d, 9, 0), outcome="opened")
        for d in (1, 2, 3, 4, 5)
    ]
    nba = recommend(
        hot_lead, _ctx(history=recent, last_contact_at=datetime(2026, 11, 5, 8, 0)),
        today=TODAY, scoring_config=scoring_config,
    )
    assert nba.suppress is True
    assert "frequency cap" in (nba.suppress_reason or "")


def test_quiet_hours_are_flagged_not_blocked(hot_lead, scoring_config):
    nba = recommend(hot_lead, _ctx(local_hour=22), today=TODAY, scoring_config=scoring_config)
    assert any("quiet hours" in f for f in nba.risk_flags)
    assert nba.suppress is False


def test_negative_history_raises_a_risk_flag(hot_lead, scoring_config):
    hist = [
        InteractionHistory(channel="email", occurred_at=datetime(2026, 11, 1, 9, 0), outcome="negative"),
        InteractionHistory(channel="call", occurred_at=datetime(2026, 11, 3, 9, 0), outcome="negative"),
    ]
    nba = recommend(hot_lead, _ctx(history=hist), today=TODAY, scoring_config=scoring_config)
    assert any("negative" in f for f in nba.risk_flags)


# ---------------------------------------------------------------------------
# Channel + content strategy
# ---------------------------------------------------------------------------
def test_channel_mix_respects_persona_preference(hot_lead, scoring_config):
    nba = recommend(hot_lead, _ctx(seniority="c_level"), today=TODAY, scoring_config=scoring_config)
    assert nba.channel_mix[0].channel in {"linkedin", "email", "call"}


def test_meeting_channel_only_for_warm_leads(cold_lead, scoring_config):
    nba = recommend(
        cold_lead,
        _ctx(lead_id="L-COLD", lifecycle_stage="new", deal_value_usd=5_000,
             last_contact_at=None, pain_points=[]),
        today=TODAY, scoring_config=scoring_config,
    )
    assert nba.recommended_channel != "meeting"


def test_content_strategy_is_stage_aware(hot_lead, scoring_config):
    new_nba = recommend(hot_lead, _ctx(lifecycle_stage="new"), today=TODAY, scoring_config=scoring_config)
    neg_nba = recommend(hot_lead, _ctx(lifecycle_stage="negotiation"), today=TODAY, scoring_config=scoring_config)
    assert new_nba.content.content_type == "cold_outreach"
    assert neg_nba.content.content_type == "objection_handling"
    assert new_nba.content.content_type != neg_nba.content.content_type


def test_pain_points_flow_into_key_messages(hot_lead, scoring_config):
    nba = recommend(
        hot_lead,
        _ctx(pain_points=["slow follow-up", "no pipeline visibility"]),
        today=TODAY, scoring_config=scoring_config,
    )
    joined = " ".join(nba.content.key_messages).lower()
    assert "slow follow-up" in joined
    assert any("slow follow-up" in h or "pipeline" in h for h in nba.content.personalisation_hooks)


def test_positive_outcome_compresses_the_cadence(hot_lead, scoring_config):
    positive = [InteractionHistory(channel="email", occurred_at=datetime(2026, 11, 4, 9, 0), outcome="replied")]
    fast = recommend(
        hot_lead, _ctx(history=positive, last_contact_at=datetime(2026, 11, 4, 9, 0)),
        today=TODAY, scoring_config=scoring_config,
    )
    slow = recommend(
        hot_lead, _ctx(history=[], last_contact_at=datetime(2026, 11, 4, 9, 0)),
        today=TODAY, scoring_config=scoring_config,
    )
    assert fast.next_touch_date <= slow.next_touch_date


# ---------------------------------------------------------------------------
# Batch / queue behaviour
# ---------------------------------------------------------------------------
def test_batch_returns_priority_sorted_queue(hot_lead, cold_lead, scoring_config):
    pairs = [
        (cold_lead, _ctx(lead_id="L-COLD", lifecycle_stage="nurture", deal_value_usd=2_000,
                         last_contact_at=None, pain_points=[])),
        (hot_lead, _ctx()),
    ]
    out = recommend_batch(pairs, today=TODAY, scoring_config=scoring_config)
    assert len(out) == 2
    assert out[0].priority_score >= out[1].priority_score
    assert out[0].lead_id == "L-HOT"


def test_recommendation_is_serialisable(hot_lead, scoring_config):
    nba = recommend(hot_lead, _ctx(), today=TODAY, scoring_config=scoring_config)
    payload = nba.model_dump_json()
    assert "next_touch_date" in payload
    assert len(payload) > 500
