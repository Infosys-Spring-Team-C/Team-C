from __future__ import annotations
from typing import Any
from ai.schemas import OutreachDraft, EvidenceItem
from ai.providers import BaseLLMProvider
from ._base import structured_task


def generate_outreach(request: dict[str, Any], provider: BaseLLMProvider) -> OutreachDraft:
    lead = request.get("lead", request)
    channel_raw = str(request.get("channel", "Email"))
    channel = "Call script" if "call" in channel_raw.lower() else ("LinkedIn" if "linkedin" in channel_raw.lower() else ("Short message" if "short" in channel_raw.lower() else "Email"))
    def mock() -> OutreachDraft:
        company = str(lead.get("company_name", "there")).strip() or "there"
        contact = str(lead.get("contact_name", "")).strip()
        first = contact.split()[0] if contact else "there"
        product = str(request.get("product_service", "our solution")).strip() or "our solution"
        objective = str(request.get("campaign_objective", "start a discovery conversation")).strip()
        cta = str(request.get("call_to_action", "Would a 15-minute conversation next week be useful?")).strip()
        tone = str(request.get("tone", "Professional")).lower()
        user_insights = str(request.get("company_insights", lead.get("user_research", ""))).strip()
        facts: list[EvidenceItem] = []
        if lead.get("industry"):
            facts.append(EvidenceItem(statement=f"Industry: {lead['industry']}", source="Supplied lead record", source_type="backend", confidence="medium"))
        if user_insights:
            facts.append(EvidenceItem(statement=user_insights[:400], source="User-provided insights", source_type="provided", confidence="medium"))
        personalization = [f"Addressed to {company} using the supplied lead record."]
        assumptions: list[str] = []
        if user_insights: personalization.append("Referenced user-provided company insight without claiming independent research.")
        else: assumptions.append("No company-specific insight was supplied; keep the message broad and validate relevance.")
        context_line = f" I saw your team is in {lead['industry']}." if lead.get("industry") else ""
        if channel == "Call script":
            body = f"Hi {first}, this is [Your name] from [Company]. I am reaching out because {objective}.{context_line} We help teams evaluate {product} when they are looking to improve a related process. Before I assume relevance, how are you approaching this today?"
            subject = None
        elif channel == "LinkedIn":
            body = f"Hi {first} — I’m reaching out because {objective}.{context_line} We help teams explore {product}. If this is on your radar, {cta.lower()}"
            subject = None
        elif channel == "Short message":
            body = f"Hi {first}, we help teams explore {product}.{context_line} {cta}"
            subject = None
        else:
            subject = f"A question about {company}'s priorities"
            body = f"Hi {first},\n\nI’m reaching out because {objective}.{context_line}\n\nWe help teams explore {product} when it is relevant to their current priorities. I don’t want to assume this is a fit — would it be useful to compare notes on how you handle this today?\n\n{cta}\n\nBest,\n[Your name]"
        if tone == "direct": body = body.replace("I don’t want to assume this is a fit — ", "")
        section = str(request.get("section_to_regenerate", ""))
        variation = str(request.get("variation_label", "primary"))
        if variation != "primary":
            # Deterministic mock alternatives visibly change the requested piece, so demo controls
            # exercise the same review flow as a real model response.
            personalization.append(f"Generated the {section.lower() or 'alternative'} variation requested by the user.")
            if section == "Subject line" and subject:
                subject = f"Quick question for {company}"
            elif section == "Opening":
                body = body.replace(f"Hi {first}", f"Hello {first}", 1)
            elif section == "Value proposition":
                body = body.replace(f"We help teams explore {product}", f"Teams use {product} to assess whether a focused process change is worthwhile")
            elif section == "Call to action":
                cta = "Would it make sense to compare notes for 15 minutes?"
                body = body.replace(str(request.get("call_to_action", "")), cta)
            elif subject:
                subject = f"A practical question for {company}"
        return OutreachDraft(channel=channel, subject_line=subject, body=body, call_to_action=cta,
            personalization_rationale=personalization, facts_used=facts, assumptions=assumptions,
            missing_context=["Confirmed pain point", "Buying timing"] if not lead.get("explicit_needs") else ["Buying timing"],
            alternative_angle=f"Test a {variation} angle focused on a specific observed priority after it is verified.")
    return structured_task(provider, "outreach", {"lead": lead, **{k:v for k,v in request.items() if k != "lead"}}, OutreachDraft, mock)
