"""Operation-routed LangGraph workflows, isolated from Streamlit session state."""
from __future__ import annotations
import time
from typing import Any
from ai.state import WorkflowState
from ai.schemas import WorkflowResponse, ExecutionRecord, ResearchResult
from ai.providers import BaseLLMProvider
from ai.agents import (analyze_lead_context, qualify_lead, generate_outreach,
                       summarize_conversation, recommend_follow_up, interpret_sales_analytics)
from utils.logging import get_logger

logger = get_logger(__name__)
VALID_OPERATIONS = {"research", "lead_intelligence", "outreach", "conversation", "follow_up", "sales_insights"}


def workflow_route(state: WorkflowState) -> str:
    op = state.get("operation", "")
    return op if op in VALID_OPERATIONS else "invalid"


def build_workflow(provider: BaseLLMProvider, checkpointer: Any | None = None):
    """Build the graph lazily; callers may pass a LangGraph checkpointer for resumability.

    No checkpointer is enabled by the Streamlit app, because persistence belongs to the approved
    backend layer. A caller may explicitly supply an in-memory or backend-approved checkpointer.
    """
    try:
        from langgraph.graph import StateGraph, START, END
    except ImportError:
        return None

    def append_trace(state: WorkflowState, name: str) -> list[str]:
        return [*state.get("trace", []), name]

    def research_node(state: WorkflowState) -> dict[str, Any]:
        try:
            result = analyze_lead_context(state["request"], provider)
            return {"research": result, "trace": append_trace(state, "research")}
        except Exception as exc:
            return {"errors": [*state.get("errors", []), f"Research workflow failed: {exc}"], "trace": append_trace(state, "research_error")}

    def qualification_node(state: WorkflowState) -> dict[str, Any]:
        try:
            research = state.get("research")
            if research is None:
                raise ValueError("Qualification requires research output")
            result = qualify_lead(state["request"], research, provider)
            return {"qualification": result, "trace": append_trace(state, "qualification")}
        except Exception as exc:
            return {"errors": [*state.get("errors", []), f"Qualification workflow failed: {exc}"], "trace": append_trace(state, "qualification_error")}

    def outreach_node(state: WorkflowState) -> dict[str, Any]:
        try: return {"result": generate_outreach(state["request"], provider), "trace": append_trace(state, "outreach")}
        except Exception as exc: return {"errors": [*state.get("errors", []), f"Outreach workflow failed: {exc}"], "trace": append_trace(state, "outreach_error")}

    def conversation_node(state: WorkflowState) -> dict[str, Any]:
        try: return {"result": summarize_conversation(state["request"], provider), "trace": append_trace(state, "conversation")}
        except Exception as exc: return {"errors": [*state.get("errors", []), f"Conversation workflow failed: {exc}"], "trace": append_trace(state, "conversation_error")}

    def follow_up_node(state: WorkflowState) -> dict[str, Any]:
        try: return {"result": recommend_follow_up(state["request"], provider), "trace": append_trace(state, "follow_up")}
        except Exception as exc: return {"errors": [*state.get("errors", []), f"Follow-up workflow failed: {exc}"], "trace": append_trace(state, "follow_up_error")}

    def insight_node(state: WorkflowState) -> dict[str, Any]:
        try: return {"result": interpret_sales_analytics(state["request"].get("analytics", {}), provider), "trace": append_trace(state, "sales_insights")}
        except Exception as exc: return {"errors": [*state.get("errors", []), f"Sales insights workflow failed: {exc}"], "trace": append_trace(state, "sales_insights_error")}

    def after_research(state: WorkflowState) -> str:
        return "qualification" if state.get("operation") == "lead_intelligence" else "finalize"

    def finalize(state: WorkflowState) -> dict[str, Any]:
        result = state.get("result")
        if state.get("operation") == "research": result = state.get("research")
        if state.get("operation") == "lead_intelligence": result = state.get("research")
        return {"result": result, "trace": append_trace(state, "finalize")}

    graph = StateGraph(WorkflowState)
    graph.add_node("dispatch", lambda state: {"trace": [*state.get("trace", []), "dispatch"]})
    graph.add_node("research", research_node)
    graph.add_node("qualification", qualification_node)
    graph.add_node("outreach", outreach_node)
    graph.add_node("conversation", conversation_node)
    graph.add_node("follow_up", follow_up_node)
    graph.add_node("sales_insights", insight_node)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "dispatch")
    graph.add_conditional_edges("dispatch", workflow_route, {
        "research": "research", "lead_intelligence": "research", "outreach": "outreach",
        "conversation": "conversation", "follow_up": "follow_up", "sales_insights": "sales_insights", "invalid": "finalize",
    })
    graph.add_conditional_edges("research", after_research, {"qualification": "qualification", "finalize": "finalize"})
    graph.add_edge("qualification", "finalize")
    for node in ("outreach", "conversation", "follow_up", "sales_insights"):
        graph.add_edge(node, "finalize")
    graph.add_edge("finalize", END)
    return graph.compile(checkpointer=checkpointer)


def _fallback_execute(operation: str, request: dict[str, Any], provider: BaseLLMProvider) -> dict[str, Any]:
    """Same routing semantics if LangGraph has not yet been installed."""
    state: dict[str, Any] = {"operation": operation, "request": request, "errors": [], "trace": ["fallback_dispatch"]}
    if operation in {"research", "lead_intelligence"}:
        state["research"] = analyze_lead_context(request, provider)
        state["trace"].append("research")
        if operation == "lead_intelligence":
            state["qualification"] = qualify_lead(request, state["research"], provider)
            state["trace"].append("qualification")
        state["result"] = state["research"]
    elif operation == "outreach": state["result"] = generate_outreach(request, provider)
    elif operation == "conversation": state["result"] = summarize_conversation(request, provider)
    elif operation == "follow_up": state["result"] = recommend_follow_up(request, provider)
    elif operation == "sales_insights": state["result"] = interpret_sales_analytics(request.get("analytics", {}), provider)
    else: state["errors"].append(f"Unsupported operation '{operation}'.")
    state["trace"].append("finalize")
    return state


def run_workflow(operation: str, request: dict[str, Any], provider: BaseLLMProvider,
                 checkpointer: Any | None = None, thread_id: str | None = None) -> WorkflowResponse:
    """Execute one operation. Optional checkpointing is opt-in and stays outside Streamlit."""
    started = time.perf_counter()
    errors: list[str] = []
    state: dict[str, Any] = {}
    try:
        if operation not in VALID_OPERATIONS:
            raise ValueError(f"Unsupported operation '{operation}'.")
        graph = build_workflow(provider, checkpointer=checkpointer)
        initial: WorkflowState = {"operation": operation, "request": request, "errors": [], "trace": [], "started_at": started}
        if graph is None:
            state = _fallback_execute(operation, request, provider)
        elif checkpointer is not None:
            state = dict(graph.invoke(initial, config={"configurable": {"thread_id": thread_id or f"salesgenie-{operation}"}}))
        else:
            state = dict(graph.invoke(initial))
        errors = list(state.get("errors", []))
    except Exception as exc:
        logger.exception("AI workflow '%s' failed", operation)
        errors.append(str(exc))
    elapsed = int((time.perf_counter() - started) * 1000)
    execution = ExecutionRecord(operation=operation, provider=provider.name, model=provider.settings.llm_model,
                                duration_ms=elapsed, success=not errors, errors=errors, used_mock=provider.is_mock)
    return WorkflowResponse(result=state.get("result"), research=state.get("research"),
                            qualification=state.get("qualification"), execution=execution, errors=errors)
