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

#: Frontend ``outreach_type`` -> AI package ``channel`` literal.
_CHANNEL_BY_TYPE = {
    "cold_email": "Email",
    "follow_up": "Email",
    "linkedin_message": "LinkedIn",
    "call_script": "Call script",
    "short_message": "Short message",
}


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
        if hasattr(value, "model_dump"):
            return value.model_dump()
        try:
            return dict(value)
        except (TypeError, ValueError) as exc:
            raise IntelligenceError(
                f"AI package returned an unsupported payload type: {type(value).__name__}"
            ) from exc

    @staticmethod
    def _validate(model: Any, payload: Any, what: str) -> Any:
        """Validate package output against the backend contract.

        A schema mismatch must surface as ``IntelligenceError`` (HTTP 502), not
        as an unhandled ``ValidationError`` (HTTP 500).
        """
        try:
            return model.model_validate(payload)
        except ValueError as exc:
            raise IntelligenceError(
                f"AI package returned {what} that does not match the backend contract: {exc}"
            ) from exc

    # -- engine interface ------------------------------------------------
    def analyze_lead(self, lead: dict[str, Any]) -> tuple[LeadIntelligence, ExecutionInfo]:
        response, info = self._run("lead_intelligence", {"lead": lead})
        if response.research is None or response.qualification is None:
            raise IntelligenceError("AI package returned no research/qualification output.")
        research = self._dump(response.research)
        qualification = self._validate(
            QualificationAssessment,
            self._dump(response.qualification),
            "a qualification assessment",
        )
        research["qualification"] = qualification.model_dump()
        return self._validate(LeadIntelligence, research, "lead intelligence"), info

    def generate_outreach(
        self, lead: dict[str, Any], request: dict[str, Any]
    ) -> tuple[OutreachDraft, ExecutionInfo]:
        response, info = self._run("outreach", self._outreach_payload(lead, request))
        if response.result is None:
            raise IntelligenceError("AI package returned no outreach draft.")
        return self._validate(OutreachDraft, self._dump(response.result), "an outreach draft"), info

    @staticmethod
    def _outreach_payload(lead: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
        """Translate the frontend request into the AI package's outreach request.

        The API speaks ``outreach_type``/``goal``/``pain_points``; the reviewed
        package reads ``channel``/``campaign_objective``/``company_insights``.
        Without this mapping those choices would be silently dropped and every
        external draft would use the package defaults.

        ``length`` has no equivalent in the package (its prompt has no length
        control), so it is not forwarded; see ``docs/ai-review.md``.
        """
        payload: dict[str, Any] = {"lead": lead, **request}
        channel = _CHANNEL_BY_TYPE.get(str(request.get("outreach_type", "")).strip().lower())
        if channel:
            payload["channel"] = channel
        if request.get("goal"):
            payload["campaign_objective"] = request["goal"]

        context: list[str] = []
        if request.get("industry"):
            context.append(f"Industry: {request['industry']}")
        pain_points = [str(item) for item in request.get("pain_points") or [] if str(item).strip()]
        if pain_points:
            context.append("Pain points: " + "; ".join(pain_points))
        # The package falls back to the lead's research only when this is empty,
        # so include it to avoid losing context.
        research = str(lead.get("user_research") or "").strip()
        if research:
            context.append(f"User research: {research}")
        if context:
            payload["company_insights"] = " | ".join(context)

        for key in ("outreach_type", "goal", "pain_points", "length"):
            payload.pop(key, None)
        return payload

    def summarize_conversation(
        self, transcript: str, notes: str
    ) -> tuple[ConversationSummary, ExecutionInfo]:
        response, info = self._run(
            "conversation", {"transcript": transcript, "notes": notes}
        )
        if response.result is None:
            raise IntelligenceError("AI package returned no conversation summary.")
        return self._validate(
            ConversationSummary, self._dump(response.result), "a conversation summary"
        ), info

    def recommend(self, lead: dict[str, Any]) -> tuple[Recommendation, ExecutionInfo]:
        response, info = self._run("follow_up", {"lead": lead})
        if response.result is None:
            raise IntelligenceError("AI package returned no recommendation.")
        return self._validate(
            Recommendation, self._dump(response.result), "a recommendation"
        ), info

    def score_lead(self, lead: dict[str, Any]) -> tuple[LeadScoreResult, ExecutionInfo]:
        started = time.perf_counter()
        try:
            from ai.scoring.rule_based import calculate_lead_score  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise IntelligenceError("The AI package does not expose ai.scoring.rule_based.") from exc
        result = self._validate(
            LeadScoreResult,
            self._dump(
                calculate_lead_score(
                    lead,
                    qualified_threshold=self.settings.score_threshold_qualified,
                    nurture_threshold=self.settings.score_threshold_nurture,
                )
            ),
            "a lead score",
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
        return self._validate(
            SalesInsightsResult, self._dump(response.result), "an analytics interpretation"
        ), info
