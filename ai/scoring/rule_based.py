"""Explainable, configurable heuristic lead score. It is deliberately not a probability model."""
from __future__ import annotations
from typing import Any
from ai.schemas import LeadScoreResult, ScoreFactor

DEFAULT_WEIGHTS: dict[str, float] = {
    "company_fit": 20, "industry_relevance": 15, "company_size": 10, "contact_role": 15,
    "engagement_history": 15, "explicit_needs": 15, "sales_stage": 5, "response_behavior": 5,
}


def _contains(value: str, words: tuple[str, ...]) -> bool:
    text = (value or "").lower()
    return any(word in text for word in words)


def _factor(name: str, weight: float, value: float, explanation: str, signal: str) -> ScoreFactor:
    return ScoreFactor(name=name.replace("_", " ").title(), weight=weight, normalized_value=value,
                       points=round(weight * value, 1), explanation=explanation, signal=signal)


def calculate_lead_score(lead: dict[str, Any], weights: dict[str, float] | None = None,
                         qualified_threshold: int = 70, nurture_threshold: int = 45) -> LeadScoreResult:
    weights = {**DEFAULT_WEIGHTS, **(weights or {})}
    # normalize arbitrary user sliders so outcomes remain 0..100
    total = sum(max(0, float(v)) for v in weights.values()) or 1
    normalized = {k: max(0, float(v)) * 100 / total for k, v in weights.items()}
    desc = str(lead.get("company_description", ""))
    research = str(lead.get("user_research", ""))
    industry = str(lead.get("industry", ""))
    size = str(lead.get("company_size", "Unknown"))
    role = str(lead.get("prospect_role", ""))
    engagement = str(lead.get("engagement_history", ""))
    needs = str(lead.get("explicit_needs", ""))
    stage = str(lead.get("stage", ""))
    response = str(lead.get("response_behavior", ""))
    company_context = " ".join([desc, research])

    vals: dict[str, tuple[float, str, str]] = {
        "company_fit": (0.8 if len(company_context.strip()) > 35 else (0.45 if company_context.strip() else 0),
          "Company context is detailed enough to assess fit." if len(company_context.strip()) > 35 else "Limited company-fit context provided.",
          "positive" if len(company_context.strip()) > 35 else "missing"),
        "industry_relevance": (0.8 if industry.strip() else 0, "Industry is identified." if industry.strip() else "Industry is not specified.", "positive" if industry.strip() else "missing"),
        "company_size": (0.7 if size not in {"", "Unknown"} else 0, "Company size is available." if size not in {"", "Unknown"} else "Company size is unknown.", "positive" if size not in {"", "Unknown"} else "missing"),
        "contact_role": (0.9 if _contains(role, ("director", "vp", "vice president", "head", "chief", "manager", "owner", "founder")) else (0.45 if role else 0),
          "Role appears to have influence." if _contains(role, ("director", "vp", "head", "chief", "manager", "owner", "founder")) else ("Role is present but influence is unclear." if role else "Contact role is unknown."),
          "positive" if role else "missing"),
        "engagement_history": (0.85 if _contains(engagement, ("meeting", "demo", "replied", "opened", "call")) else (0.35 if engagement else 0),
          "Recorded engagement includes a meaningful interaction." if _contains(engagement, ("meeting", "demo", "replied", "opened", "call")) else ("Only limited engagement context is available." if engagement else "No engagement history is supplied."),
          "positive" if engagement else "missing"),
        "explicit_needs": (1.0 if len(needs.strip()) > 15 else (0.4 if needs.strip() else 0),
          "Explicit customer needs are documented." if len(needs.strip()) > 15 else ("A short need signal is available." if needs.strip() else "No explicit customer need is supplied."),
          "positive" if needs.strip() else "missing"),
        "sales_stage": (0.9 if stage in {"Proposal", "Negotiation"} else (0.65 if stage in {"Discovery", "Qualified"} else (0.35 if stage else 0)),
          f"Current sales stage: {stage or 'not provided'}.", "positive" if stage else "missing"),
        "response_behavior": (0.85 if _contains(response, ("positive", "responded", "replied", "interested", "booked")) else (0.2 if _contains(response, ("no response", "unsubscribed", "declined")) else (0.4 if response else 0)),
          "Response behavior is positive." if _contains(response, ("positive", "responded", "replied", "interested", "booked")) else ("Response behavior suggests low engagement." if response else "No response behavior recorded."),
          "positive" if _contains(response, ("positive", "responded", "replied", "interested", "booked")) else ("negative" if _contains(response, ("no response", "unsubscribed", "declined")) else "missing")),
    }
    factors = [_factor(key, normalized[key], *vals[key]) for key in DEFAULT_WEIGHTS]
    score = int(round(sum(f.points for f in factors)))
    category = "Qualified" if score >= qualified_threshold else ("Nurture" if score >= nurture_threshold else "Low priority")
    positives = [f.explanation for f in factors if f.signal == "positive"]
    negatives = [f.explanation for f in factors if f.signal == "negative"]
    missing = [f.explanation for f in factors if f.signal == "missing"]
    action = "Schedule a discovery conversation and validate decision process." if category == "Qualified" else ("Collect missing fit and need information before the next outreach." if category == "Nurture" else "Enrich the record or use a lightweight, permissioned nurture touch.")
    return LeadScoreResult(score=score, qualification_category=category, factors=factors,
        positive_signals=positives, negative_signals=negatives, missing_information=missing,
        recommended_next_action=action)
