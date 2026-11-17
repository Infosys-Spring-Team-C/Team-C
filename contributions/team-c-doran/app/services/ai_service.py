"""Internal outreach generation service.

This deterministic implementation provides a usable local draft generator. It
can be replaced by an LLM-backed implementation without changing the API.
"""

from typing import Any
import asyncio
import inspect
from collections.abc import Callable
from typing import TypeVar

_Result = TypeVar("_Result")
AI_CALL_TIMEOUT_SECONDS = 5.0


async def invoke_with_timeout(
    service_function: Callable[..., _Result], *args: Any
) -> _Result:
    """Run a sync or async AI service function with a five-second deadline.

    Synchronous service functions run in a worker thread so they cannot block
    the event loop. A timed-out thread may finish in the background, but the
    HTTP request stops waiting and returns control within the deadline.
    """
    async def call_service() -> _Result:
        if inspect.iscoroutinefunction(service_function):
            result = await service_function(*args)  # type: ignore[misc]
        else:
            result = await asyncio.to_thread(service_function, *args)
        if inspect.isawaitable(result):
            return await result  # type: ignore[misc, no-any-return]
        return result

    return await asyncio.wait_for(call_service(), timeout=AI_CALL_TIMEOUT_SECONDS)


def generate_outreach_email(
    lead_data: dict[str, Any], tone: str
) -> dict[str, str]:
    """Generate an outreach draft using only the lead profile and supplied focus.

    The function avoids inventing company facts. Integrations can replace this
    implementation while preserving the same input and output contract.
    """
    contact_name = str(lead_data.get("contact_name") or "there").strip()
    company_name = str(lead_data.get("company_name") or "your team").strip()
    industry = str(lead_data.get("industry") or "your industry").strip()
    focus_points = str(lead_data.get("focus_points") or "").strip()
    focus_sentence = (
        f"I would be glad to discuss {focus_points}."
        if focus_points
        else f"I would be glad to learn about your priorities at {company_name}."
    )
    tone_label = tone.strip().lower()

    subject = f"A conversation about {company_name}'s priorities"
    content = (
        f"Hi {contact_name},\n\n"
        f"I’m reaching out to connect with {company_name} in the {industry} space. "
        f"{focus_sentence}\n\n"
        "Would you be open to a brief conversation this week?\n\n"
        "Best,\nSalesGenie"
    )
    follow_up = (
        f"If there is no reply, send a brief, {tone_label} follow-up after 3 business days. "
        "If there is still no response, make one final follow-up a week later with a concise "
        "summary of the proposed conversation."
    )
    return {
        "email_subject": subject,
        "email_content": content,
        "follow_up_strategy": follow_up,
    }


def score_lead(lead_dict: dict[str, Any]) -> dict[str, Any]:
    """Calculate a transparent baseline lead score from available profile data.

    The scoring service can be replaced by a model-backed implementation while
    preserving this response contract.
    """
    score = 25
    factors: dict[str, object] = {"baseline": {"points": 25}}

    funding_stage = str(lead_dict.get("funding_stage") or "").strip().lower()
    funding_points = (
        15
        if funding_stage and funding_stage not in {"bootstrapped", "pre-seed"}
        else 5
        if funding_stage
        else 0
    )
    score += funding_points
    factors["funding_stage"] = {"value": funding_stage or None, "points": funding_points}

    tech_stack = str(lead_dict.get("tech_stack") or "").strip()
    tech_points = 15 if tech_stack else 0
    score += tech_points
    factors["tech_stack"] = {"present": bool(tech_stack), "points": tech_points}

    company_size = str(lead_dict.get("company_size") or "").strip()
    size_points = 15 if company_size else 0
    score += size_points
    factors["company_size"] = {"value": company_size or None, "points": size_points}

    revenue = lead_dict.get("revenue")
    revenue_points = 20 if isinstance(revenue, (int, float)) and revenue > 0 else 0
    score += revenue_points
    factors["revenue"] = {"provided": revenue is not None, "points": revenue_points}

    lead_status = str(lead_dict.get("status") or "new").lower()
    status_points = {"new": 0, "contacted": 5, "qualified": 10, "closed": 15}.get(
        lead_status, 0
    )
    score += status_points
    factors["status"] = {"value": lead_status, "points": status_points}

    score = min(score, 100)
    priority = "high" if score >= 70 else "medium" if score >= 40 else "low"
    return {
        "lead_score": score,
        "conversion_probability": round(score / 100, 2),
        "priority_level": priority,
        "scoring_factors": factors,
    }
