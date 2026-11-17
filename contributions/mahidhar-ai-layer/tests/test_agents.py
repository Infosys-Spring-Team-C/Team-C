"""Tests for the LangGraph-style orchestration (Day 3 architecture, Day 33 wiring)."""
from __future__ import annotations

import pytest

from sales_intel.ai.agents.lead_agent import (
    StateGraph,
    build_lead_agent,
    node_load_lead,
    run_lead_agent,
)


def test_graph_runs_nodes_in_order(hot_lead, qualified_context):
    out = run_lead_agent(hot_lead, qualified_context)
    assert out["trace"] == [
        "load_lead", "score_lead", "summarise", "next_best_action", "compose_outreach", "persist"
    ]
    assert out["score"]["lead_id"] == "L-HOT"
    assert out["nba"]["priority"] in {"P0", "P1", "P2", "P3"}
    assert out["errors"] == []


def test_graph_without_optional_nodes(hot_lead, qualified_context):
    out = run_lead_agent(hot_lead, qualified_context, include_summary=False, include_outreach=False)
    assert out["trace"] == ["load_lead", "score_lead", "next_best_action", "persist"]
    assert out["outreach"] is None


def test_outreach_falls_back_to_template_without_llm(hot_lead, qualified_context):
    """The agent must still produce a usable draft with no API key."""
    out = run_lead_agent(hot_lead, qualified_context)
    draft = out["outreach"]
    assert draft["engine"] == "template"
    assert draft["subject"]
    assert len(draft["body"]) > 40
    assert draft["call_to_action"]


def test_graph_rejects_mismatched_ids(hot_lead, qualified_context):
    bad = qualified_context.model_copy(update={"lead_id": "NOPE"})
    with pytest.raises(ValueError, match="mismatch"):
        run_lead_agent(hot_lead, bad)


def test_load_lead_node_validates_input():
    with pytest.raises(Exception):
        node_load_lead({"lead": {"lead_id": "X"}, "context": {"lead_id": "Y"}})


def test_graph_persists_score_and_nba(hot_lead, qualified_context):
    from sales_intel.db.repository import get_repository

    run_lead_agent(hot_lead, qualified_context)
    repo = get_repository()
    assert len(repo.scores) == 1
    assert len(repo.nbas) == 1


def test_stategraph_conditional_routing():
    g = StateGraph()
    g.add_node("start", lambda s: {**s, "flag": s.get("value", 0) > 5})
    g.add_node("high", lambda s: {**s, "branch": "high"})
    g.add_node("low", lambda s: {**s, "branch": "low"})
    g.set_entry_point("start")
    g.add_conditional_edges("start", lambda s: "high" if s["flag"] else "low",
                            {"high": "high", "low": "low"})
    assert g.invoke({"value": 9})["branch"] == "high"
    assert g.invoke({"value": 1})["branch"] == "low"


def test_stategraph_step_limit_prevents_infinite_loops():
    g = StateGraph()
    g.add_node("a", lambda s: s)
    g.add_node("b", lambda s: s)
    g.set_entry_point("a")
    g.add_edge("a", "b")
    g.add_edge("b", "a")           # deliberate cycle
    out = g.invoke({}, max_steps=6)
    assert len(out["trace"]) == 6  # terminates instead of hanging


def test_graph_includes_summary_when_transcript_supplied(hot_lead, qualified_context):
    ctx = qualified_context.model_copy(update={
        "transcript": "Priya: I'll send the quote by Friday.\nClient: Please share the SOC 2 report.\n"
    })
    out = run_lead_agent(hot_lead, ctx)
    assert out["summary"] is not None
    assert out["summary"]["action_items"]
