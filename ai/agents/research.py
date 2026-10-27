from __future__ import annotations
from typing import Any
from ai.schemas import ResearchResult, EvidenceItem, Hypothesis
from ai.providers import BaseLLMProvider
from ._base import structured_task


def analyze_lead_context(request: dict[str, Any], provider: BaseLLMProvider) -> ResearchResult:
    lead = request.get("lead", request)
    product = str(request.get("product_service", "your offering")).strip() or "your offering"
    def mock() -> ResearchResult:
        company = str(lead.get("company_name", "This company")).strip() or "This company"
        facts: list[EvidenceItem] = []
        for field, label in [("industry", "Industry"), ("company_size", "Company size"), ("company_description", "Description"), ("prospect_role", "Prospect role"), ("user_research", "User-provided research")]:
            value = str(lead.get(field, "")).strip()
            if value and value != "Unknown":
                facts.append(EvidenceItem(statement=f"{label}: {value}", source="User-provided context", source_type="provided", confidence="high" if field in {"industry", "prospect_role"} else "medium"))
        context_text = " ".join(str(lead.get(k, "")) for k in ("industry", "company_description", "user_research")).lower()
        challenges = [Hypothesis(statement=f"{company} may need to improve the workflow related to {product}.", rationale="Hypothesis derived from the supplied company context; validate in discovery.")]
        if "growth" in context_text or "scale" in context_text:
            challenges.append(Hypothesis(statement="Growth may be creating process or capacity pressure.", rationale="The supplied context references growth or scale; this is not a verified business challenge.", confidence="medium"))
        needs = [Hypothesis(statement=f"Evaluate whether {product} addresses a current operational or commercial priority.", rationale="No explicit need was provided, so this is a discovery hypothesis.")]
        if str(lead.get("explicit_needs", "")).strip():
            needs = [Hypothesis(statement=str(lead["explicit_needs"]), rationale="Explicitly supplied lead context.", confidence="medium", requires_validation=False)]
        missing = [label for key, label in [("website", "Website or retrieved company material"), ("company_description", "Company description"), ("prospect_role", "Prospect role and buying influence"), ("explicit_needs", "Confirmed customer need"), ("engagement_history", "Engagement history")]
                   if not str(lead.get(key, "")).strip() or str(lead.get(key)) == "Unknown"]
        return ResearchResult(
            company_overview=f"{company} is described only through the supplied lead context. No external website retrieval was performed.",
            supported_facts=facts,
            potential_challenges=challenges,
            possible_needs=needs,
            opportunities=[Hypothesis(statement=f"Explore whether {product} can support the prospect's stated priorities.", rationale="Potential opportunity; requires discovery confirmation.")],
            product_industry_fit=f"Fit cannot be confirmed from the available context. Compare {product} to the stated industry and use case during discovery.",
            buyer_role_relevance=(f"The recorded role is {lead.get('prospect_role')}; confirm its decision authority, priorities, and stakeholders." if lead.get("prospect_role") else "No buyer role is supplied; identify the economic buyer, users, and champion."),
            qualification_insights=["Treat all opportunity statements as hypotheses until the customer validates them."],
            discovery_questions=[f"What priority would make it worthwhile to evaluate {product}?", "How is this handled today, and what is not working?", "Who else would evaluate or approve a change?", "What outcome and timing would define success?"],
            missing_information=missing,
            confidence="medium" if len(facts) >= 3 else "low",
        )
    return structured_task(provider, "research", {"lead": lead, "product_service": product}, ResearchResult, mock)
