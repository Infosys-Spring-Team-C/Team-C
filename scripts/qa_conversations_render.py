"""Headless render check for the Conversations page (Module 5).

This is **not** a browser walkthrough.  It runs ``frontend/app.py`` through
Streamlit's own ``AppTest`` harness against a live API, so it proves that the
page renders the expected sections with real data - the step a data-contract
test cannot prove - without a desktop browser.

Usage
-----
Start the API first, then::

    python scripts/qa_conversations_render.py --base-url http://127.0.0.1:8011 \
        --email qa.admin@example.com --password "<password>"

Exit code ``0`` when every expected section rendered, ``1`` when one is
missing or the script raised, ``2`` when the API cannot be reached.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

EXPECTED_SECTIONS = (
    "New summary",
    "Latest summary",
    "CRM sync status",
    "Run a sync",
    "Field mapping",
    "Recent activity",
    "History",
)


def _api(base: str, path: str, token: str | None = None, method: str = "GET",
         payload: dict | None = None) -> httpx.Response:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx.request(method, f"{base}{path}", headers=headers, json=payload,
                         timeout=30.0)


def seed(base: str, token: str) -> int:
    suffix = datetime.now(timezone.utc).strftime("%H%M%S%f")
    lead = _api(base, "/api/v1/leads", token, "POST", {
        "company_name": f"QA Render {suffix}",
        "contact_name": "Noor Haddad",
        "email": f"qa.render.{suffix}@example.com",
        "industry": "Logistics",
        "company_size": "500-1000",
        "annual_revenue": "USD 120M",
        "stage": "qualified",
    })
    lead.raise_for_status()
    lead_id = lead.json()["id"]

    summary = _api(base, "/api/v1/conversations/summarize", token, "POST", {
        "lead_id": lead_id,
        "interaction_type": "call",
        "transcript": (
            "Noor said the current forecast is a spreadsheet. "
            "Noor will share the file by Thursday. "
            "They want a pricing review next week."
        ),
    })
    summary.raise_for_status()

    for operation in ("sync_contact", "activity_log", "update_stage"):
        response = _api(base, "/api/v1/crm/sync", token, "POST", {
            "provider": "salesforce",
            "operation": operation,
            "lead_ids": [lead_id],
            "simulate": True,
        })
        response.raise_for_status()
    return lead_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("UAT_BASE_URL",
                                                        "http://127.0.0.1:8011"))
    parser.add_argument("--email", default=os.getenv("UAT_EMAIL"))
    parser.add_argument("--password", default=os.getenv("UAT_PASSWORD"))
    args = parser.parse_args(argv)

    base = args.base_url.rstrip("/")
    if not args.email or not args.password:
        print("Provide --email/--password or set UAT_EMAIL/UAT_PASSWORD.")
        return 2

    try:
        token_response = httpx.post(
            f"{base}/api/v1/auth/token",
            data={"username": args.email, "password": args.password},
            timeout=15.0,
        )
    except httpx.HTTPError as exc:
        print(f"Cannot reach {base}: {exc.__class__.__name__}: {exc}")
        return 2
    if token_response.status_code != 200:
        print(f"Sign-in failed: {token_response.status_code} {token_response.text[:200]}")
        return 2
    token = token_response.json()["access_token"]

    lead_id = seed(base, token)
    print(f"Seeded probe lead {lead_id} with one summary and three simulated syncs.")

    os.environ["SALES_GENIE_BACKEND_BASE_URL"] = base
    os.environ["SALES_GENIE_BACKEND_TOKEN"] = token

    from streamlit.testing.v1 import AppTest

    app_path = str(Path(__file__).resolve().parents[1] / "frontend" / "app.py")
    at = AppTest.from_file(app_path, default_timeout=120)
    at.session_state["nav"] = "conversations"
    at.session_state["backend_url"] = base
    at.run()

    failures: list[str] = []
    if at.exception:
        for exc in at.exception:
            failures.append(f"exception: {exc.value}")
    rendered = "\n".join(str(getattr(item, "value", "")) for item in at.markdown)
    rendered += "\n".join(str(getattr(item, "value", "")) for item in at.caption)
    for section in EXPECTED_SECTIONS:
        if section not in rendered:
            failures.append(f"section not rendered: {section!r}")

    # The page must say that the transport is simulated, never that it is live.
    if "Simulated transport" not in rendered:
        failures.append("the simulated-transport disclaimer is missing")

    _api(base, f"/api/v1/leads/{lead_id}", token, "DELETE")

    if failures:
        print(f"FAIL - {len(failures)} problem(s):")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(f"PASS - {len(EXPECTED_SECTIONS)} sections rendered with live data, "
          "no exception, simulated-transport disclaimer present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
