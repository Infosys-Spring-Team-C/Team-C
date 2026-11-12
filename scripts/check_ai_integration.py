"""Manual smoke test for the reviewed AI package (``SALES_GENIE_AI_BACKEND=external``).

Run this after Mahidhar's AI pull request is merged, and before claiming the
external engine works:

    python scripts/check_ai_integration.py

It constructs the real ``ExternalAIEngine`` with the provider selected by
``SALES_GENIE_LLM_PROVIDER`` (default: the deterministic **mock** provider, no
API key and no network) and exercises all six operations.  Every result is
validated against ``backend.intelligence.contract``, so a schema drift between
the package and the backend fails here rather than in the UI.

Exit codes: 0 = all operations passed, 1 = at least one failed,
2 = the AI package is not installed in this checkout.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Running a file inside scripts/ puts scripts/ on sys.path, not the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

LEAD = {
    "id": "1",
    "company_name": "Acme Systems",
    "industry": "Software",
    "company_size": "51-200",
    "company_description": "A growing B2B software company modernising its reporting stack.",
    "contact_name": "Dana Scully",
    "prospect_role": "Director of Sales Operations",
    "engagement_history": "Discovery meeting booked and attended.",
    "explicit_needs": "Reduce manual reporting effort across the sales team this quarter.",
    "response_behavior": "Interested and responded quickly",
    "user_research": "Met at a conference; evaluating two vendors.",
    "stage": "proposal",
}

TRANSCRIPT = (
    "Dana explained that reporting is manual and slow. "
    "Dana will send the current spreadsheet by Friday. "
    "She is interested in an integration demo next month."
)

OUTREACH_REQUEST = {
    "tone": "professional",
    "length": "medium",
    "outreach_type": "cold_email",
    "goal": "book a discovery call",
    "industry": "Software",
    "pain_points": ["manual reporting"],
    "product_service": "SalesGenie AI",
    "call_to_action": "Would a short call next week be useful?",
}

ANALYTICS = {
    "pipeline_distribution": [
        {"stage": "prospecting", "count": 5},
        {"stage": "qualified", "count": 2},
    ],
    "activity_trend": [
        {"date": "2026-10-01", "activity": 1},
        {"date": "2026-10-02", "activity": 4},
    ],
}


def main() -> int:
    import os

    from backend.config import Settings
    from backend.intelligence.contract import IntelligenceError
    from backend.intelligence.external import ExternalAIEngine

    # Default to the deterministic mock so the gate stays offline-safe, but honour
    # the configured provider when the caller explicitly selects one.
    provider = os.getenv("SALES_GENIE_LLM_PROVIDER", "mock").strip() or "mock"
    model = os.getenv("SALES_GENIE_LLM_MODEL", "").strip()
    settings = Settings(
        ai_backend="external",
        ai_provider=provider,
        ai_model=model,
        groq_api_key=os.getenv("GROQ_API_KEY", "") or os.getenv("GROK_API_KEY", ""),
        groq_base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        google_api_key=os.getenv("GOOGLE_API_KEY", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        jwt_secret="smoke-only-secret-value-0123456789",
    )

    try:
        engine = ExternalAIEngine(settings)
    except IntelligenceError as exc:
        print(f"SKIP: {exc}")
        return 2

    checks = [
        ("analyze_lead", lambda: engine.analyze_lead(LEAD)),
        ("generate_outreach", lambda: engine.generate_outreach(LEAD, OUTREACH_REQUEST)),
        ("summarize_conversation", lambda: engine.summarize_conversation(TRANSCRIPT, "")),
        ("recommend", lambda: engine.recommend(LEAD)),
        ("score_lead", lambda: engine.score_lead(LEAD)),
        ("interpret_analytics", lambda: engine.interpret_analytics(ANALYTICS)),
    ]

    failures = 0
    for name, call in checks:
        try:
            result, info = call()
        except Exception as exc:  # noqa: BLE001 - report, do not mask
            failures += 1
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")
            continue

        detail = ""
        if name == "score_lead":
            detail = (
                f" score={result.score} factors={len(result.factors)}"
                f" probability={result.conversion_probability}"
            )
        elif name == "analyze_lead":
            detail = f" category={result.qualification.category}"
        elif name == "generate_outreach":
            detail = f" channel={result.channel}"
        print(
            f"PASS {name}: engine={info.engine} provider={info.provider}"
            f" model={info.model} used_mock={info.used_mock}{detail}"
        )

    total = len(checks)
    print(f"\n{total - failures}/{total} operations passed")
    if failures:
        print("The external engine is NOT ready. Do not claim it works.")
        return 1
    print("External engine produced validated output for every operation.")
    if provider == "mock":
        print("Note: this used the mock provider. Real model calls are still unverified.")
    else:
        print(f"Live provider '{provider}' returned validated output for every operation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
