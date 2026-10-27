from __future__ import annotations
from typing import Any
from ai.schemas import Recommendation, EvidenceItem
from ai.providers import BaseLLMProvider
from ._base import structured_task


def recommend_follow_up(request: dict[str, Any], provider: BaseLLMProvider) -> Recommendation:
    lead = request.get("lead", request)
    def mock() -> Recommendation:
        name = str(lead.get("company_name", "Selected lead"))
        engagement = str(lead.get("engagement_history", "")).strip()
        needs = str(lead.get("explicit_needs", "")).strip()
        evidence = []
        if engagement: evidence.append(EvidenceItem(statement=engagement, source="Lead record", source_type="backend", confidence="medium"))
        if needs: evidence.append(EvidenceItem(statement=needs, source="Lead record", source_type="backend", confidence="medium"))
        priority = "High" if needs and engagement else ("Medium" if engagement or needs else "Low")
        action = "Send a tailored recap and request a discovery meeting." if engagement else "Research and verify a relevant business priority before outreach."
        reason = "The lead record contains an interaction or a stated need." if evidence else "The available record has no verified interaction or need, so enrichment should come first."
        contact_words = str(lead.get("contact_name", "")).split()
        first_name = contact_words[0] if contact_words else "there"
        return Recommendation(lead_id=str(lead.get("id")) if lead.get("id") else None, related_lead=name,
            recommended_action=action, reason=reason, supporting_evidence=evidence, priority=priority,
            suggested_timing="Within one business day" if engagement else None,
            follow_up_draft=(f"Hi {first_name}, thanks for the context. Would it be useful to align on the next discovery step?" if evidence else None))
    return structured_task(provider, "follow_up", {"lead": lead}, Recommendation, mock)
