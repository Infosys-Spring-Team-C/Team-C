from __future__ import annotations
from typing import Any
from ai.schemas import QualificationAssessment, ResearchResult
from ai.providers import BaseLLMProvider
from ._base import structured_task


def qualify_lead(request: dict[str, Any], research: ResearchResult, provider: BaseLLMProvider) -> QualificationAssessment:
    lead = request.get("lead", request)
    def mock() -> QualificationAssessment:
        role = str(lead.get("prospect_role", "")).strip()
        needs = str(lead.get("explicit_needs", "")).strip()
        engagement = str(lead.get("engagement_history", "")).strip()
        complete = len(research.supported_facts) >= 3 and bool(role)
        category = "Qualified" if complete and needs else ("Nurture" if complete else "Needs discovery")
        positive = [f"{len(research.supported_facts)} supplied fact(s) are available for qualification."]
        if needs: positive.append("An explicit customer need was supplied.")
        gaps = research.missing_information[:]
        if not engagement: gaps.append("No engagement signal is available.")
        return QualificationAssessment(category=category,
            fit_assessment="There is enough supplied context for an initial discovery hypothesis." if complete else "Company fit is not yet established from the supplied context.",
            buyer_relevance=f"{role} should be validated for decision influence and ownership." if role else "No buyer role is available.",
            engagement_assessment=engagement or "No engagement history was supplied.",
            positive_signals=positive, risks_or_gaps=gaps,
            recommended_next_step="Run a focused discovery conversation to validate need, stakeholders, urgency, and current process.",
            confidence="medium" if complete else "low")
    return structured_task(provider, "qualification", {"lead": lead, "research": research.model_dump()}, QualificationAssessment, mock)
