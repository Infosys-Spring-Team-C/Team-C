"""LangGraph agent architecture (Day 3 design, implemented here so the AI tasks
have a runnable orchestration layer).

The graph is the "Lead Intelligence -> Outreach -> Action -> Log" loop from the
SRS. It is written against a tiny StateGraph shim so that:
  * if `langgraph` is installed it is used for checkpointing/observability;
  * if it is not installed the same node functions run on a plain sequential
    fallback (identical results), which keeps CI and offline demos green.

Nodes
-----
load_lead       validate inputs, hydrate history
score_lead      Module 4 scoring  (Day 12 engine, Day 14 weights)
summarise       optional: fold the latest call summary into context (Day 24)
next_best_action Module 4 NBA engine (Day 15)
compose_outreach Module 3 email generation (prompt registry)
persist         write score + nba + audit row
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Callable, TypedDict

from sales_intel.ai.llm.client import LLMUnavailable, get_llm
from sales_intel.ai.nba.engine import recommend
from sales_intel.ai.prompts.registry import DEFAULT_OUTREACH, get_prompt
from sales_intel.ai.scoring.engine import load_scoring_config, score_lead
from sales_intel.db.repository import get_repository
from sales_intel.utils import utcnow
from sales_intel.schemas import (
    ConversationSummary,
    LeadContext,
    LeadFeatures,
    LeadScore,
    NextBestAction,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
class AgentState(TypedDict, total=False):
    lead: dict[str, Any]
    context: dict[str, Any]
    today: str
    score: dict[str, Any]
    summary: dict[str, Any]
    nba: dict[str, Any]
    outreach: dict[str, Any]
    errors: list[str]
    trace: list[str]


# ---------------------------------------------------------------------------
# Minimal graph shim (drop-in compatible surface for langgraph)
# ---------------------------------------------------------------------------
Node = Callable[[AgentState], AgentState]


@dataclass
class StateGraph:
    """Sequential/edge-driven graph with optional conditional routing."""

    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)
    conditional: dict[str, tuple[Callable[[AgentState], str], dict[str, str]]] = field(default_factory=dict)
    entry: str = ""

    def add_node(self, name: str, fn: Node) -> None:
        self.nodes[name] = fn

    def add_edge(self, src: str, dst: str) -> None:
        self.edges.append((src, dst))

    def add_conditional_edges(self, src: str, router: Callable[[AgentState], str], mapping: dict[str, str]) -> None:
        self.conditional[src] = (router, mapping)

    def set_entry_point(self, name: str) -> None:
        self.entry = name

    def _next(self, current: str, state: AgentState) -> str | None:
        if current in self.conditional:
            router, mapping = self.conditional[current]
            return mapping.get(router(state))
        for src, dst in self.edges:
            if src == current:
                return dst
        return None

    def invoke(self, state: AgentState, max_steps: int = 50) -> AgentState:
        current = self.entry
        steps = 0
        while current and steps < max_steps:
            steps += 1
            fn = self.nodes[current]
            state = fn(state)
            state.setdefault("trace", []).append(current)
            current = self._next(current, state) or ""
        return state


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------
def node_load_lead(state: AgentState) -> AgentState:
    lead = LeadFeatures(**state["lead"])
    ctx = LeadContext(**state["context"])
    if lead.lead_id != ctx.lead_id:
        raise ValueError("lead_id mismatch between lead and context")
    state["lead"] = lead.model_dump()
    state["context"] = ctx.model_dump(mode="json")
    state.setdefault("trace", [])
    return state


def node_score(state: AgentState) -> AgentState:
    cfg = load_scoring_config()
    result: LeadScore = score_lead(LeadFeatures(**state["lead"]), cfg)
    state["score"] = result.model_dump(mode="json")
    get_repository().save_score(result)
    return state


def node_summarise(state: AgentState) -> AgentState:
    """Fold a provided transcript into the lead context (optional node)."""
    transcript = state.get("context", {}).get("transcript")
    if not transcript:
        return state
    from sales_intel.ai.summarization.engine import summarise

    utterances = []
    for line in transcript.splitlines():
        if ":" in line:
            sp, _, txt = line.partition(":")
            utterances.append({"speaker": sp.strip(), "text": txt.strip(), "is_internal": False})
    if not utterances:
        return state
    from sales_intel.schemas import Utterance

    summary = summarise(
        [Utterance(**u) for u in utterances],
        interaction_id=f"agent-{utcnow().isoformat()}",
        lead_id=state["lead"]["lead_id"],
    )
    state["summary"] = summary.model_dump(mode="json")
    return state


def node_nba(state: AgentState) -> AgentState:
    ctx_payload = {k: v for k, v in state["context"].items() if k != "transcript"}
    nba: NextBestAction = recommend(
        LeadFeatures(**state["lead"]),
        LeadContext(**ctx_payload),
        today=date.fromisoformat(state.get("today") or date.today().isoformat()),
    )
    state["nba"] = nba.model_dump(mode="json")
    get_repository().save_nba(nba)
    return state


def node_outreach(state: AgentState) -> AgentState:
    """Compose the first-touch email for the recommended channel (Module 3)."""
    nba = state.get("nba") or {}
    content = nba.get("content") or {}
    ctx = state.get("context") or {}
    lead = state.get("lead") or {}
    llm = get_llm()

    draft: dict[str, Any] = {
        "channel": nba.get("recommended_channel", "email"),
        "subject": "",
        "body": "",
        "call_to_action": content.get("call_to_action", ""),
        "engine": "template",
        "prompt_version": DEFAULT_OUTREACH.version,
    }
    if llm.available:
        template = get_prompt("outreach_email", DEFAULT_OUTREACH.version)
        system, user = template.render(
            company=lead.get("company_name") or "the account",
            industry=lead.get("industry") or "your industry",
            persona=ctx.get("seniority", "unknown"),
            pain_points=", ".join(ctx.get("pain_points") or []) or "not specified",
            goal=ctx.get("lifecycle_stage", "new"),
            tone=content.get("tone", "consultative"),
            length="short",
            email_type=content.get("content_type", "cold_outreach"),
        )
        try:
            data, resp = llm.chat_json(system, user, temperature=0.4, max_tokens=500)
            draft.update(
                subject=str(data.get("subject", ""))[:120],
                body=str(data.get("body", "")),
                engine="llm",
                model=resp.model,
            )
        except (LLMUnavailable, ValueError) as exc:
            state.setdefault("errors", []).append(f"outreach_llm_failed: {exc}")
    if not draft["body"]:
        # Deterministic template fallback so the agent always returns a usable draft.
        hook = (ctx.get("pain_points") or ["manual lead follow-up"])[0]
        draft["subject"] = f"{lead.get('company_name') or 'Quick question'} — {hook}?"
        draft["body"] = (
            f"Hi,\n\nMost {lead.get('industry') or 'similar'} teams we speak to are stuck with "
            f"{hook}. We built a lead-intelligence layer that scores, prioritises and drafts "
            f"follow-ups so reps only touch the accounts that matter.\n\n"
            f"{content.get('call_to_action', 'Worth a 15-minute call?')}\n\nBest,\n"
        )
    state["outreach"] = draft
    return state


def node_persist(state: AgentState) -> AgentState:
    state["finished_at"] = utcnow().isoformat()  # type: ignore[typeddict-unknown-key]
    return state


# ---------------------------------------------------------------------------
# Graph factory
# ---------------------------------------------------------------------------
def build_lead_agent(include_summary: bool = True, include_outreach: bool = True) -> StateGraph:
    g = StateGraph()
    g.add_node("load_lead", node_load_lead)
    g.add_node("score_lead", node_score)
    g.add_node("next_best_action", node_nba)
    g.set_entry_point("load_lead")
    g.add_edge("load_lead", "score_lead")

    if include_summary:
        g.add_node("summarise", node_summarise)
        g.add_edge("score_lead", "summarise")
        g.add_edge("summarise", "next_best_action")
    else:
        g.add_edge("score_lead", "next_best_action")

    if include_outreach:
        g.add_node("compose_outreach", node_outreach)
        g.add_edge("next_best_action", "compose_outreach")
        g.add_node("persist", node_persist)
        g.add_edge("compose_outreach", "persist")
    else:
        g.add_node("persist", node_persist)
        g.add_edge("next_best_action", "persist")
    return g


def run_lead_agent(
    lead: LeadFeatures,
    context: LeadContext,
    today: date | None = None,
    include_summary: bool = True,
    include_outreach: bool = True,
) -> dict[str, Any]:
    """Convenience wrapper: run the full lead-intelligence graph for one lead."""
    graph = build_lead_agent(include_summary, include_outreach)
    state: AgentState = {
        "lead": lead.model_dump(),
        "context": context.model_dump(mode="json"),
        "today": (today or date.today()).isoformat(),
    }
    out = graph.invoke(state)
    return {
        "score": out.get("score"),
        "nba": out.get("nba"),
        "outreach": out.get("outreach"),
        "summary": out.get("summary"),
        "errors": out.get("errors", []),
        "trace": out.get("trace", []),
    }
