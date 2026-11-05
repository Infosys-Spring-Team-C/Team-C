"""Unit tests for the deterministic intelligence engine and the AI boundary."""
from __future__ import annotations

import pytest

from backend.config import Settings, get_settings
from backend.intelligence import (
    IntelligenceError,
    get_engine,
    reset_engine_cache,
)
from backend.intelligence.contract import LeadScoreResult, ScoreFactor
from backend.intelligence.external import ExternalAIEngine
from backend.intelligence.heuristic import HeuristicEngine

RICH_LEAD = {
    "id": "1",
    "company_name": "Acme Systems",
    "industry": "Software",
    "company_description": "A growing B2B software company modernising its reporting stack.",
    "company_size": "51-200",
    "prospect_role": "Director of Sales Operations",
    "engagement_history": "Discovery meeting booked and attended.",
    "explicit_needs": "Reduce manual reporting effort across the sales team this quarter.",
    "response_behavior": "Interested and responded quickly",
    "stage": "proposal",
    "contact_name": "Dana Scully",
}


@pytest.fixture()
def engine() -> HeuristicEngine:
    return HeuristicEngine(get_settings())


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def test_score_is_bounded_deterministic_and_explainable(engine):
    first, info = engine.score_lead(RICH_LEAD)
    second, _ = engine.score_lead(RICH_LEAD)

    assert first == second, "heuristic scoring must be deterministic"
    assert 0 <= first.score <= 100
    assert first.qualification_category in {"Qualified", "Nurture", "Low priority"}
    assert len(first.factors) == 4
    assert abs(sum(f.weight for f in first.factors) - 100) < 0.001
    assert all(0 <= f.normalized_value <= 1 for f in first.factors)
    assert all(f.explanation for f in first.factors)
    assert info.used_mock is True
    assert info.engine == "heuristic"


def test_missing_information_lowers_the_score(engine):
    empty, _ = engine.score_lead({})
    rich, _ = engine.score_lead(RICH_LEAD)
    assert empty.score < rich.score
    assert empty.missing_information
    assert rich.score >= get_settings().score_threshold_qualified


def test_heuristic_never_returns_a_calibrated_probability(engine):
    result, _ = engine.score_lead(RICH_LEAD)
    assert result.conversion_probability is None
    assert "not be read as a statistical probability" in result.probability_note
    assert "Not a trained or calibrated predictive model" in result.methodology_note


def test_score_factor_bounds_are_validated():
    with pytest.raises(ValueError):
        ScoreFactor(
            name="Broken",
            weight=10,
            normalized_value=1.5,
            points=15,
            explanation="out of range",
            signal="positive",
        )
    with pytest.raises(ValueError):
        LeadScoreResult(
            score=101,
            qualification_category="Qualified",
            factors=[],
            recommended_next_action="none",
        )


def test_negative_response_behaviour_does_not_inflate_intent(engine):
    positive = engine.score_lead({**RICH_LEAD, "response_behavior": "Interested"})[0]
    negative = engine.score_lead(
        {**RICH_LEAD, "response_behavior": "Not interested, unsubscribed"}
    )[0]
    assert negative.score <= positive.score


# ---------------------------------------------------------------------------
# Company analysis
# ---------------------------------------------------------------------------
def test_analysis_separates_facts_from_hypotheses(engine):
    result, info = engine.analyze_lead(RICH_LEAD)

    assert result.supported_facts
    assert all(fact.source_type in {"provided", "backend"} for fact in result.supported_facts)
    assert result.potential_challenges
    assert all(hypothesis.requires_validation for hypothesis in result.potential_challenges)
    assert result.discovery_questions
    assert "No website retrieval" in result.company_overview
    assert "No website or external company research was performed" in result.disclaimer
    assert result.qualification.category == "Qualified"
    assert info.duration_ms >= 0


def test_analysis_reports_missing_information_without_inventing(engine):
    result, _ = engine.analyze_lead({"company_name": "Bare Co"})
    assert result.missing_information
    assert any("Website" in item for item in result.missing_information)
    assert any("Confirmed customer need" in item for item in result.missing_information)
    assert result.confidence == "low"
    assert result.qualification.category == "Needs discovery"


# ---------------------------------------------------------------------------
# Outreach
# ---------------------------------------------------------------------------
def _request(**overrides):
    payload = {
        "tone": "professional",
        "length": "medium",
        "outreach_type": "cold_email",
        "goal": "start a discovery conversation",
        "pain_points": ["manual reporting"],
        "product_service": "SalesGenie AI",
        "call_to_action": "Would a short call help?",
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    ("outreach_type", "channel"),
    [
        ("cold_email", "Email"),
        ("linkedin_message", "LinkedIn"),
        ("call_script", "Call script"),
        ("short_message", "Short message"),
    ],
)
def test_outreach_channel_mapping(engine, outreach_type, channel):
    draft, _ = engine.generate_outreach(RICH_LEAD, _request(outreach_type=outreach_type))
    assert draft.channel == channel
    assert draft.body
    assert draft.call_to_action


def test_outreach_tone_and_length_change_the_body(engine):
    formal, _ = engine.generate_outreach(RICH_LEAD, _request(tone="formal"))
    friendly, _ = engine.generate_outreach(RICH_LEAD, _request(tone="friendly"))
    short, _ = engine.generate_outreach(RICH_LEAD, _request(length="short"))
    long, _ = engine.generate_outreach(RICH_LEAD, _request(length="long"))

    assert formal.body.startswith("Dear")
    assert "Best," in friendly.body
    assert len(short.body) < len(long.body)


def test_outreach_greeting_skips_titles(engine):
    lead = {**RICH_LEAD, "contact_name": "Dr. Sofia Alvarez"}
    draft, _ = engine.generate_outreach(lead, _request())
    assert draft.body.startswith("Hi Sofia,")
    assert "Hi Dr.," not in draft.body


def test_outreach_greeting_helper_skips_titles():
    from ai.agents._base import contact_first_name

    assert contact_first_name("Dr. Sofia Alvarez") == "Sofia"
    assert contact_first_name("Prof. Lee Chan") == "Lee"
    assert contact_first_name("Priya Nair") == "Priya"
    assert contact_first_name("") == "there"


def test_outreach_without_pain_points_declares_the_assumption(engine):
    draft, _ = engine.generate_outreach(RICH_LEAD, _request(pain_points=[]))
    assert any("No pain point was supplied" in item for item in draft.assumptions)
    assert draft.missing_context


def test_outreach_does_not_invent_industry_specific_claims(engine):
    lead = {**RICH_LEAD, "industry": ""}
    draft, _ = engine.generate_outreach(lead, _request())
    assert any("Industry is unknown" in item for item in draft.assumptions)
    assert "I understand" not in draft.body


# ---------------------------------------------------------------------------
# Conversation intelligence
# ---------------------------------------------------------------------------
def test_conversation_summary_extracts_only_supplied_action_items(engine):
    transcript = (
        "Dana said the reporting process is manual and slow. "
        "Dana will send the current spreadsheet by Friday."
    )
    summary, _ = engine.summarize_conversation(transcript, "")
    assert summary.action_items
    assert summary.action_items[0].owner == "Dana"
    assert summary.action_items[0].evidence
    assert "Extracted only from the supplied transcript" in summary.source_note


def test_conversation_summary_does_not_invent_commitments(engine):
    summary, _ = engine.summarize_conversation(
        "We discussed the weather and the general market.", ""
    )
    assert summary.action_items == []
    assert any("No explicit action item" in item for item in summary.missing_or_uncertain)


def test_conversation_summary_handles_empty_input(engine):
    summary, _ = engine.summarize_conversation("", "")
    assert summary.executive_summary == "No analyzable content was supplied."


# ---------------------------------------------------------------------------
# Recommendations and analytics interpretation
# ---------------------------------------------------------------------------
def test_recommendation_priority_follows_evidence(engine):
    high, _ = engine.recommend(RICH_LEAD)
    low, _ = engine.recommend({"company_name": "Bare Co"})
    assert high.priority == "High"
    assert high.supporting_evidence
    assert high.suggested_channel == "email"
    assert low.priority == "Low"
    assert low.supporting_evidence == []
    # No outreach is justified for an empty record, so no channel is invented.
    assert low.suggested_channel is None


def test_analytics_interpretation_is_observation_only(engine):
    result, _ = engine.interpret_analytics(
        {
            "pipeline_distribution": [
                {"stage": "prospecting", "count": 5},
                {"stage": "qualified", "count": 2},
            ],
            "activity_trend": [
                {"date": "2026-10-01", "activity": 1},
                {"date": "2026-10-02", "activity": 4},
            ],
        }
    )
    assert result.insights
    assert any("prospecting" in insight.observation for insight in result.insights)
    assert "do not establish causes or forecast" in result.caveat


def test_analytics_interpretation_without_data_is_honest(engine):
    result, _ = engine.interpret_analytics({})
    assert len(result.insights) == 1
    assert result.insights[0].title == "Insufficient analytics"
    assert result.insights[0].confidence == "low"


# ---------------------------------------------------------------------------
# Engine selection / external adapter
# ---------------------------------------------------------------------------
def test_external_backend_fails_loudly_when_package_is_absent(monkeypatch):
    # Simulate a checkout where the AI package was not merged.
    import sys

    monkeypatch.setitem(sys.modules, "ai.graph", None)
    with pytest.raises(IntelligenceError) as excinfo:
        ExternalAIEngine(get_settings())
    assert "reviewed AI package" in str(excinfo.value)
    assert "SALES_GENIE_AI_BACKEND=heuristic" in str(excinfo.value)


def test_external_engine_initialises_with_the_mock_provider():
    engine = ExternalAIEngine(
        Settings(ai_backend="external", ai_provider="mock", jwt_secret="x" * 32)
    )
    assert engine.name == "external"
    assert engine.provider == "mock"


def test_external_engine_rejects_grok_with_a_clear_message():
    with pytest.raises(IntelligenceError) as excinfo:
        ExternalAIEngine(
            Settings(ai_backend="external", ai_provider="grok", jwt_secret="x" * 32)
        )
    assert "grok" in str(excinfo.value).lower()
    assert "SALES_GENIE_AI_BACKEND=heuristic" in str(excinfo.value)


def test_external_score_maps_eight_factors_onto_four_dimensions():
    engine = ExternalAIEngine(
        Settings(ai_backend="external", ai_provider="mock", jwt_secret="x" * 32)
    )
    result, info = engine.score_lead(RICH_LEAD)
    assert len(result.factors) == 8
    assert {factor.dimension for factor in result.factors} == {
        "Fit",
        "Intent",
        "Engagement",
        "Decision readiness",
    }
    assert result.conversion_probability is None
    assert info.model == "rule-based"


def test_external_recommendation_derives_a_channel_from_the_draft():
    engine = ExternalAIEngine(
        Settings(ai_backend="external", ai_provider="mock", jwt_secret="x" * 32)
    )
    result, _ = engine.recommend(RICH_LEAD)
    assert result.follow_up_draft
    assert result.suggested_channel == "email"


def test_unsupported_backend_is_a_configuration_error(monkeypatch):
    monkeypatch.setattr(
        "backend.intelligence.get_settings",
        lambda: Settings(ai_backend="mystery", jwt_secret="x" * 20),
    )
    reset_engine_cache()
    try:
        with pytest.raises(IntelligenceError) as excinfo:
            get_engine()
        assert "Unsupported SALES_GENIE_AI_BACKEND" in str(excinfo.value)
    finally:
        reset_engine_cache()


def test_default_engine_is_the_external_ai_package():
    assert Settings(jwt_secret="x" * 32).ai_backend == "external"
