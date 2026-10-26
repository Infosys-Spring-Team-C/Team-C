"""Adapter around the separately-reviewed AI package.

The AI layer (LangGraph agents, prompts, providers, scoring) is contributed to
this repository through its own pull request.  Until then the backend runs on
``backend.intelligence.heuristic``.  When the reviewed package is present, set::

    SALES_GENIE_AI_BACKEND=external
    SALES_GENIE_LLM_PROVIDER=grok|gemini|mock
    SALES_GENIE_LLM_MODEL=<model>

This module translates between the AI package's public interface
(``ai.graph.run_workflow``, ``ai.providers.create_provider``,
``ai.scoring.rule_based.calculate_lead_score``) and this repository's typed
contract.  No agent code is imported by the API layer and no agent code is
copied here.
"""
from __future__ import annotations

import time
from typing import Any

from backend.config import Settings
from backend.intelligence.contract import (
    ConversationSummary,
    ExecutionInfo,
    IntelligenceError,
    LeadIntelligence,
    LeadScoreResult,
    OutreachDraft,
    QualificationAssessment,
    Recommendation,
    SalesInsightsResult,
)


class ExternalAIEngine:
    """Thin, validating adapter; it performs no AI work itself."""

    name = "external"

    def __init__(self, settings: Settings):
        self.settings = settings
        try:
            from ai.graph import run_workflow  # type: ignore
            from ai.providers import ProviderError, create_provider  # type: ignore
            from utils.config import get_settings as ai_settings  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on external PR
            raise IntelligenceError(
                "SALES_GENIE_AI_BACKEND=external was requested but the reviewed AI "
                "package (ai.* / utils.*) is not installed in this checkout. Merge the "
                "AI pull request or set SALES_GENIE_AI_BACKEND=heuristic."
            ) from exc

        self._run_workflow = run_workflow
        self._provider_error = ProviderError
        overrides = {
            "demo_mode": settings.ai_provider == "mock",
            "llm_provider": settings.ai_provider,
            "llm_model": settings.ai_model,
            "llm_temperature": settings.ai_temperature,
            "request_timeout_seconds": settings.ai_timeout_seconds,
            "grok_api_key": settings.grok_api_key,
            "google_api_key": settings.google_api_key,
        }
        try:
            self._provider = create_provider(ai_settings(overrides=overrides))
        except Exception as exc:  # pragma: no cover - provider configuration error
            raise IntelligenceError(f"Could not initialise the AI provider: {exc}") from exc

        self.provider = getattr(self._provider, "name", settings.ai_provider)
        self.model = settings.ai_model or "unspecified"

    # -- helpers ---------------------------------------------------------
    def _run(self, operation: str, request: dict[str, Any]):
        started = time.perf_counter()
        response = self._run_workflow(operation, request, self._provider)
        if response.errors:
            raise IntelligenceError("; ".join(response.errors))
        info = ExecutionInfo(
            engine=self.name,
            provider=getattr(response.execution, "provider", self.provider),
            model=getattr(response.execution, "model", self.model) or self.model,
            duration_ms=int((time.perf_counter() - started) * 1000),
            used_mock=bool(getattr(response.execution, "used_mock", False)),
        )
        return response, info

    @staticmethod
    def _dump(value: Any) -> dict[str, Any]:
        return value.model_dump() if hasattr(value, "model_dump") else dict(value)

    # -- engine interface ------------------------------------------------
    def analyze_lead(self, lead: dict[str, Any]) -> tuple[LeadIntelligence, ExecutionInfo]:
        response, info = self._run("lead_intelligence", {"lead": lead})
        if response.research is None or response.qualification is None:
            raise IntelligenceError("AI package returned no research/qualification output.")
        research = self._dump(response.research)
        qualification = QualificationAssessment.model_validate(self._dump(response.qualification))
        research["qualification"] = qualification.model_dump()
        return LeadIntelligence.model_validate(research), info

    def generate_outreach(
        self, lead: dict[str, Any], request: dict[str, Any]
    ) -> tuple[OutreachDraft, ExecutionInfo]:
        response, info = self._run("outreach", {"lead": lead, **request})
        if response.result is None:
            raise IntelligenceError("AI package returned no outreach draft.")
        return OutreachDraft.model_validate(self._dump(response.result)), info

    def summarize_conversation(
        self, transcript: str, notes: str
    ) -> tuple[ConversationSummary, ExecutionInfo]:
        response, info = self._run(
            "conversation", {"transcript": transcript, "notes": notes}
        )
        if response.result is None:
            raise IntelligenceError("AI package returned no conversation summary.")
        return ConversationSummary.model_validate(self._dump(response.result)), info

    def recommend(self, lead: dict[str, Any]) -> tuple[Recommendation, ExecutionInfo]:
        response, info = self._run("follow_up", {"lead": lead})
        if response.result is None:
            raise IntelligenceError("AI package returned no recommendation.")
        return Recommendation.model_validate(self._dump(response.result)), info

    def score_lead(self, lead: dict[str, Any]) -> tuple[LeadScoreResult, ExecutionInfo]:
        started = time.perf_counter()
        try:
            from ai.scoring.rule_based import calculate_lead_score  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise IntelligenceError("The AI package does not expose ai.scoring.rule_based.") from exc
        result = LeadScoreResult.model_validate(
            self._dump(calculate_lead_score(lead, qualified_threshold=self.settings.score_threshold_qualified,
                                            nurture_threshold=self.settings.score_threshold_nurture))
        )
        info = ExecutionInfo(
            engine=self.name,
            provider=self.provider,
            model="rule-based",
            duration_ms=int((time.perf_counter() - started) * 1000),
            used_mock=False,
        )
        return result, info

    def interpret_analytics(
        self, analytics: dict[str, Any]
    ) -> tuple[SalesInsightsResult, ExecutionInfo]:
        response, info = self._run("sales_insights", {"analytics": analytics})
        if response.result is None:
            raise IntelligenceError("AI package returned no analytics interpretation.")
        return SalesInsightsResult.model_validate(self._dump(response.result)), info
