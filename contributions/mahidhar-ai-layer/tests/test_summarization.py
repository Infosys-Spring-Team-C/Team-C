"""Tests for the Day-24 conversation summarisation service."""
from __future__ import annotations

from datetime import date, datetime

import pytest

from sales_intel.ai.llm.client import LLMClient, LLMUnavailable
from sales_intel.ai.summarization.engine import (
    _detect_owner,
    _topic_of,
    heuristic_summarise,
    parse_due_date,
    summarise,
    to_interaction_record,
)
from sales_intel.schemas import ConversationSummary, Utterance


# ---------------------------------------------------------------------------
# Day parsing
# ---------------------------------------------------------------------------
MEETING = date(2026, 11, 4)  # a Wednesday


@pytest.mark.parametrize(
    "hint,expected",
    [
        ("tomorrow", date(2026, 11, 5)),
        ("today", date(2026, 11, 4)),
        ("in two weeks", date(2026, 11, 18)),
        ("in 3 days", date(2026, 11, 7)),
        ("next week", date(2026, 11, 11)),
        ("by Friday", date(2026, 11, 6)),
        ("end of week", date(2026, 11, 6)),
        ("12/11", date(2026, 11, 12)),
        ("on 12 Nov", date(2026, 11, 12)),
        ("next month", date(2026, 12, 4)),
    ],
)
def test_parse_due_date(hint, expected):
    assert parse_due_date(hint, MEETING) == expected


def test_parse_due_date_returns_none_without_a_date():
    assert parse_due_date(None, MEETING) is None
    assert parse_due_date("at some point maybe", MEETING) is None


# ---------------------------------------------------------------------------
# Topic + owner detection
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "text,topic",
    [
        ("The pricing is too high for our budget", "pricing"),
        ("We need this live by January", "timeline"),
        ("Does your API support a HubSpot sync?", "integration"),
        ("Our CISO needs the SOC 2 report", "security"),
        ("Can we get a demo next week?", "demo"),
        ("Salesforce felt too heavy for us", "competition"),
    ],
)
def test_topic_detection(text, topic):
    assert _topic_of(text) == topic


def test_owner_detection_first_person():
    owner, side = _detect_owner("I'll send the proposal by Friday", "Priya", {"priya"}, {"Priya", "Client"})
    assert owner == "Priya"
    assert side == "internal"


def test_owner_detection_customer_commitment():
    owner, side = _detect_owner(
        "Please share the security documentation", "Priya", {"priya"}, {"Priya", "Client"}
    )
    assert owner == "Client"
    assert side == "customer"


def test_owner_detection_unassigned():
    owner, side = _detect_owner("The team needs to review it", "Client", {"priya"}, {"Priya", "Client"})
    assert side in {"unassigned", "customer"}


# ---------------------------------------------------------------------------
# Heuristic engine
# ---------------------------------------------------------------------------
def test_heuristic_summary_extracts_actions_and_points(sales_call):
    s = heuristic_summarise(sales_call, "INT-1", lead_id="L-HOT", meeting_date=MEETING)
    assert s.engine == "heuristic"
    assert s.summary
    assert s.key_discussion_points, "must identify discussion points"
    assert s.action_items, "must extract at least one action item"
    assert all(a.task and a.source_quote for a in s.action_items)
    assert s.next_step
    assert 0.0 <= s.talk_ratio_internal <= 1.0
    assert s.confidence > 0


def test_heuristic_finds_competitor_and_objection(sales_call):
    s = heuristic_summarise(sales_call, "INT-1", meeting_date=MEETING)
    assert "Salesforce" in s.competitors_mentioned
    assert s.objections, "the price concern should surface as an objection"


def test_heuristic_assigns_due_dates(sales_call):
    s = heuristic_summarise(sales_call, "INT-1", meeting_date=MEETING)
    assert any(a.due_date is not None for a in s.action_items)
    assert any(a.due_hint for a in s.action_items)


def test_heuristic_handles_empty_transcript():
    s = heuristic_summarise([], "INT-EMPTY")
    assert "No usable transcript" in s.summary
    assert s.action_items == []
    assert s.confidence == 0.0


def test_large_transcript_is_bounded(sales_call):
    big = sales_call * 40
    s = heuristic_summarise(big, "INT-BIG", meeting_date=MEETING)
    assert len(s.key_discussion_points) <= 6
    assert len(s.action_items) <= 10


def test_summary_respects_noise_and_small_talk():
    chatter = [
        Utterance(speaker="A", text="Hi how are you doing today, nice weather"),
        Utterance(speaker="B", text="Doing well, thanks, traffic was bad"),
    ]
    s = heuristic_summarise(chatter, "INT-CHAT", meeting_date=MEETING)
    assert s.action_items == []
    assert s.confidence < 0.5


# ---------------------------------------------------------------------------
# Dispatcher / LLM degradation
# ---------------------------------------------------------------------------
def test_summarise_falls_back_without_a_provider(sales_call):
    s = summarise(sales_call, "INT-1", meeting_date=MEETING)
    assert s.engine == "heuristic"
    assert s.action_items


def test_summarise_falls_back_when_llm_raises(sales_call):
    class Boom(LLMClient):
        @property
        def available(self):  # noqa: D401
            return True

        def chat_json(self, *a, **k):
            raise LLMUnavailable("simulated outage")

    s = summarise(sales_call, "INT-1", meeting_date=MEETING, llm=Boom(api_key="fake"))
    assert s.engine == "heuristic"


def test_summarise_rejects_empty_input():
    with pytest.raises(ValueError):
        summarise([], "INT-X")


def test_llm_path_is_used_when_available(sales_call):
    payload = {
        "summary": "Client will pilot in Q1 pending a CISO security review.",
        "key_discussion_points": [
            {"topic": "pricing", "detail": "Price above budget", "sentiment": "negative", "quote": "It is higher"}
        ],
        "action_items": [
            {"task": "Send revised quote", "owner": "Priya", "owner_side": "internal",
             "due_hint": "tomorrow", "priority": "high", "source_quote": "I'll send a revised quote"}
        ],
        "decisions": ["Proceed with pilot"],
        "objections": ["Price above budget"],
        "competitors_mentioned": ["Salesforce"],
        "next_step": "Technical call next week",
        "overall_sentiment": "positive",
    }

    class FakeLLM(LLMClient):
        @property
        def available(self):
            return True

        def chat_json(self, *a, **k):
            from sales_intel.ai.llm.client import LLMResponse

            return payload, LLMResponse(text="{}", model="fake-model", latency_ms=12)

    s = summarise(sales_call, "INT-1", meeting_date=MEETING, llm=FakeLLM(api_key="fake"))
    assert s.engine == "llm"
    assert s.model == "fake-model"
    assert s.action_items[0].owner == "Priya"
    assert s.action_items[0].due_date == date(2026, 11, 5)
    assert s.competitors_mentioned == ["Salesforce"]
    assert s.confidence >= 0.55


def test_malformed_llm_action_items_are_dropped_not_fatal(sales_call):
    payload = {
        "summary": "Summary text.",
        "key_discussion_points": [{"topic": "pricing", "detail": "ok", "sentiment": "neutral"}],
        "action_items": [
            {"task": "Valid task here", "owner": "Priya", "due_hint": "tomorrow"},
            {"task": "", "owner": "Nobody"},          # dropped: empty task
            "not-a-dict",                               # dropped: wrong type
        ],
        "next_step": "Follow up",
    }

    class FakeLLM(LLMClient):
        @property
        def available(self):
            return True

        def chat_json(self, *a, **k):
            from sales_intel.ai.llm.client import LLMResponse

            return payload, LLMResponse(text="{}", model="fake", latency_ms=5)

    s = summarise(sales_call, "INT-1", meeting_date=MEETING, llm=FakeLLM(api_key="fake"))
    assert len(s.action_items) == 1
    assert s.action_items[0].task == "Valid task here"


def test_empty_llm_response_falls_back(sales_call):
    class EmptyLLM(LLMClient):
        @property
        def available(self):
            return True

        def chat_json(self, *a, **k):
            from sales_intel.ai.llm.client import LLMResponse

            return {"summary": "", "key_discussion_points": [], "action_items": []}, \
                LLMResponse(text="{}", model="fake", latency_ms=1)

    s = summarise(sales_call, "INT-1", meeting_date=MEETING, llm=EmptyLLM(api_key="fake"))
    assert s.engine == "heuristic"


# ---------------------------------------------------------------------------
# CRM payload
# ---------------------------------------------------------------------------
def test_interaction_record_shape(sales_call):
    s = heuristic_summarise(sales_call, "INT-1", lead_id="L-HOT", meeting_date=MEETING)
    rec = to_interaction_record(s)
    assert rec["interaction_id"] == "INT-1"
    assert rec["lead_id"] == "L-HOT"
    assert rec["open_action_count"] == len(s.action_items)
    assert rec["high_priority_count"] <= rec["open_action_count"]
    assert isinstance(rec["key_points"], list)
    # must be JSON-serialisable for the API
    import json

    json.dumps(rec)


def test_summary_serialises_round_trip(sales_call):
    s = heuristic_summarise(sales_call, "INT-1", meeting_date=MEETING)
    assert ConversationSummary.model_validate_json(s.model_dump_json()).interaction_id == "INT-1"
