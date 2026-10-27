"""End-to-end smoke test for the Streamlit frontend's compatibility layer.

The Streamlit app talks to the Team-C API through ``frontend/api_compat.py``.
This script makes the same calls the UI makes, against a live server, so the
translation is proven end to end instead of only in unit tests.

Start the API first (SQLite is enough)::

    $env:DATABASE_URL="sqlite:///./_frontend_smoke.db"
    $env:AUTH_ENABLED="false"
    $env:JWT_SECRET="smoke-only-secret-value-0123456789"
    $env:SALES_GENIE_AI_BACKEND="external"      # optional; heuristic also works
    $env:SALES_GENIE_LLM_PROVIDER="mock"
    uvicorn main:app --port 8010

Then::

    $env:SALES_GENIE_BACKEND_BASE_URL="http://127.0.0.1:8010"
    python scripts/check_frontend_integration.py

Exit codes: 0 = every check passed, 1 = at least one failed.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from frontend import api_compat  # noqa: E402


def main() -> int:
    base = api_compat.resolve_base_url()
    tag = uuid.uuid4().hex[:8]
    print(f"API: {base}")

    failures = 0
    checks: list[tuple[str, bool, str]] = []

    def record(name: str, ok: bool, detail: str = "") -> None:
        nonlocal failures
        if not ok:
            failures += 1
        checks.append((name, ok, detail))
        print(f"{'PASS' if ok else 'FAIL'} {name}{(': ' + detail) if detail else ''}")

    ok, health = api_compat.api_get(base, "/health", timeout=5)
    record("health", ok, str(health.get("ai_backend", "")) if isinstance(health, dict) else "")

    ok, created = api_compat.api_post(
        base,
        "/leads/",
        json_data={
            "company_name": f"Smoke {tag} Ltd",
            "industry": "Software",
            "contact_name": "Dana Smoke",
            "email": f"dana.{tag}@smoke.test",
            "phone": "+10000000000",
            "company_size": "51-200",
            "funding_stage": "Series B",
            "business_need": "Reduce manual reporting effort across the sales team.",
            "lead_status": "Qualified",
        },
    )
    lead_id = (created or {}).get("lead", {}).get("lead_id") if ok else None
    record("create lead", bool(ok and lead_id), f"lead_id={lead_id}")
    if not lead_id:
        print("\nCannot continue without a lead id.")
        return 1

    ok, leads = api_compat.api_get(base, "/leads/")
    found = ok and any(str(item.get("lead_id")) == str(lead_id) for item in leads)
    record("list leads", bool(found), f"{len(leads) if ok else 0} lead(s)")

    ok, insight = api_compat.api_post(base, f"/intelligence/analyze/{lead_id}")
    analysed = bool(
        ok
        and insight.get("business_needs")
        and not insight["business_needs"].startswith("No explicit need")
        and insight.get("qualification_category")
    )
    record("analyze lead (POST)", analysed,
           f"{insight.get('qualification_category', '')} / {insight.get('confidence', '')}"
           if ok else str(insight))

    ok, saved_insight = api_compat.api_get(base, f"/intelligence/analyze/{lead_id}")
    record("analyze lead (GET saved)", bool(ok and saved_insight.get("business_needs")),
           f"{saved_insight.get('qualification_category', '')}" if ok else str(saved_insight))

    ok, score = api_compat.api_post(base, f"/intelligence/score/{lead_id}")
    record("score lead (POST)", bool(ok and isinstance(score.get("lead_score"), int)),
           f"score={score.get('lead_score') if ok else '?'} "
           f"probability={score.get('conversion_probability') if ok else '?'}")

    ok, latest = api_compat.api_get(base, f"/intelligence/score/{lead_id}")
    record("score lead (GET latest)", bool(ok and isinstance(latest.get("lead_score"), int)))

    ok, draft = api_compat.api_post(
        base, "/intelligence/outreach", json_data={"lead_id": lead_id, "tone": "professional"}
    )
    record("generate outreach", bool(ok and draft.get("email_content")),
           draft.get("email_subject", "") if ok else str(draft))

    ok, saved = api_compat.api_get(base, f"/intelligence/outreach/{lead_id}")
    record("load saved outreach", bool(ok and saved.get("email_content")))

    ok, dashboard = api_compat.api_get(base, "/analytics/dashboard")
    record("analytics dashboard", bool(ok and isinstance(dashboard.get("total_leads"), int)),
           f"total={dashboard.get('total_leads') if ok else '?'}")

    ok, send = api_compat.api_post(
        base,
        "/outreach/send-email",
        json_data={"lead_id": lead_id, "recipient_email": f"dana.{tag}@smoke.test",
                   "subject": "Hi", "body": "Hello"},
    )
    record("send email is honestly unavailable",
           (not ok) and send.get("configured") is False and send.get("success") is False,
           str(send.get("message", ""))[:60])

    ok, bulk = api_compat.api_post(
        base,
        "/leads/bulk",
        json_data=[
            {
                "company_name": f"Bulk A {tag}",
                "industry": "Logistics",
                "contact_name": "A Contact",
                "email": f"a.{tag}@bulk.test",
                "business_need": "Automate exception handling.",
                "lead_status": "New",
            },
            {
                "company_name": f"Bulk B {tag}",
                "industry": "Retail",
                "contact_name": "B Contact",
                "email": f"b.{tag}@bulk.test",
                "business_need": "Improve reporting.",
                "lead_status": "New",
            },
        ],
    )
    record("bulk CSV import", bool(ok), str(bulk.get("message", "")) if ok else str(bulk))

    total = len(checks)
    print(f"\n{total - failures}/{total} frontend checks passed")
    if failures:
        print("The frontend compatibility layer is NOT ready. Do not claim it works.")
        return 1
    print("Every UI call was translated and answered by the Team-C API.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
