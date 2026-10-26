"""Live user-acceptance (UAT) runner for the SalesGenie AI backend.

This script drives a **running** API over real HTTP. It is deliberately separate
from ``pytest``: the pytest suite runs the app in-process with an isolated
database, while this runner proves the deployed application answers real
requests, persists to a real database and honours the documented error
behaviour.

Usage
-----
Start the application first (see ``docs/qa/uat-plan.md``), then::

    python scripts/qa_uat.py --base-url http://127.0.0.1:8011 \
        --email qa.admin@example.com --password "<password>"

Credentials may also be supplied through ``UAT_EMAIL`` / ``UAT_PASSWORD``.

Exit code is ``0`` when every workflow passes, ``1`` when any workflow fails and
``2`` when the environment is not reachable. A Markdown and JSON report are
written to ``docs/qa/evidence/`` unless ``--no-write`` is given.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover - environment guard
    print("httpx is required: pip install -r requirements-dev.txt")
    raise SystemExit(2)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "docs" / "qa" / "evidence"


@dataclass
class Result:
    """Outcome of one UAT workflow."""

    id: str
    title: str
    requirement: str
    status: str
    detail: str
    duration_ms: int = 0
    evidence: list[str] = field(default_factory=list)


class Failed(AssertionError):
    """Raised by :func:`expect` when an acceptance check does not hold."""


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise Failed(message)


class Runner:
    def __init__(self, base_url: str, email: str, password: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.password = password
        self.token: str | None = None
        self.results: list[Result] = []
        self.state: dict[str, Any] = {}
        self.client = httpx.Client(base_url=self.base_url, timeout=30.0)

    # -- plumbing ---------------------------------------------------------
    def auth(self, token: str | None = None) -> dict[str, str]:
        token = token if token is not None else self.token
        return {"Authorization": f"Bearer {token}"} if token else {}

    def login(self, email: str, password: str) -> httpx.Response:
        return self.client.post(
            "/api/v1/auth/token",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    def run(self, result_id: str, title: str, requirement: str,
            fn: Callable[[Result], None]) -> None:
        started = time.perf_counter()
        record = Result(result_id, title, requirement, "PASS", "")
        try:
            fn(record)
        except Failed as exc:
            record.status = "FAIL"
            record.detail = str(exc)
        except httpx.HTTPError as exc:
            record.status = "FAIL"
            record.detail = f"transport error: {exc.__class__.__name__}: {exc}"
        except Exception as exc:  # noqa: BLE001 - report, never abort the run
            record.status = "FAIL"
            record.detail = f"unexpected {exc.__class__.__name__}: {exc}"
        record.duration_ms = int((time.perf_counter() - started) * 1000)
        self.results.append(record)
        flag = record.status
        print(f"[{flag}] {record.id}  {record.title}"
              + (f"  -> {record.detail}" if record.detail else ""))

    def note(self, record: Result, line: str) -> None:
        record.evidence.append(line)

    # -- workflows --------------------------------------------------------
    def uat_01_health(self, r: Result) -> None:
        response = self.client.get("/api/v1/health")
        expect(response.status_code == 200, f"expected 200, got {response.status_code}")
        body = response.json()
        expect(body.get("status") == "ok", f"status not ok: {body.get('status')}")
        expect(body.get("database") == "ok", f"database not ok: {body.get('database')}")
        self.note(r, f"health={json.dumps(body, sort_keys=True)}")

    def uat_02_login(self, r: Result) -> None:
        response = self.login(self.email, self.password)
        expect(response.status_code == 200,
               f"login failed: {response.status_code} {response.text[:200]}")
        token = response.json().get("access_token")
        expect(bool(token), "no access_token in response")
        self.token = token
        me = self.client.get("/api/v1/auth/me", headers=self.auth())
        expect(me.status_code == 200, f"/me returned {me.status_code}")
        profile = me.json()
        expect(profile.get("role") == "admin",
               f"expected admin role, got {profile.get('role')!r}")
        self.note(r, f"token_type=bearer expires_in={response.json().get('expires_in')}")
        self.note(r, f"me={json.dumps(profile, sort_keys=True)}")

    def uat_03_bad_password(self, r: Result) -> None:
        response = self.login(self.email, "definitely-not-the-password")
        expect(response.status_code == 401,
               f"expected 401, got {response.status_code}")
        expect(response.json().get("code") == "invalid_credentials",
               f"unexpected code: {response.text[:200]}")
        self.note(r, f"body={response.text[:200]}")

    def uat_04_unauthenticated(self, r: Result) -> None:
        response = self.client.get("/api/v1/leads")
        expect(response.status_code == 401,
               f"expected 401 without a token, got {response.status_code}")
        self.note(r, f"body={response.text[:200]}")

    def uat_05_create_lead(self, r: Result) -> None:
        suffix = datetime.now(timezone.utc).strftime("%H%M%S")
        self.state["suffix"] = suffix
        email = f"ada.uat.{suffix}@northwind.example"
        payload = {
            "company_name": "UAT Northwind Logistics",
            "industry": "Logistics",
            "contact_name": "Ada Fernandes",
            "email": email,
            "phone": "+1 415 555 0134",
            "website": "northwind.example",
            "company_size": "250-500",
            "annual_revenue": "USD 40M",
            "funding_stage": "Series B",
            "tech_stack": "Salesforce, Snowflake, dbt",
            "company_description": "Regional freight and last-mile logistics operator.",
            "prospect_role": "VP Operations",
            "engagement_history": "Opened two newsletters, attended a webinar.",
            "explicit_needs": "Reduce manual dispatch planning.",
            "response_behavior": "Responds within one business day.",
            "user_research": "Public 10-K mentions fleet automation investment.",
            "pain_points": "Manual dispatch planning; high driver turnover",
            "lead_source": "Webinar",
            "stage": "qualified",
        }
        response = self.client.post("/api/v1/leads", json=payload, headers=self.auth())
        expect(response.status_code == 201,
               f"expected 201, got {response.status_code}: {response.text[:300]}")
        lead = response.json()
        expect(lead.get("company_name") == payload["company_name"],
               "company name not echoed back")
        expect(lead.get("email") == payload["email"], "email not normalised/echoed")
        expect(lead.get("website", "").startswith("http"), "website not normalised to a URL")
        expect(lead.get("stage") == "qualified", f"stage not stored: {lead.get('stage')!r}")
        self.state["lead_id"] = lead["id"]
        self.state["lead_email"] = lead["email"]
        self.note(r, f"created lead id={lead['id']} stage={lead.get('stage')} "
                     f"status={lead.get('status')}")

    def uat_06_duplicates(self, r: Result) -> None:
        lead_id = self.state.get("lead_id")
        expect(bool(lead_id), "no lead created by UAT-05")
        duplicate = self.client.post(
            "/api/v1/leads",
            json={"company_name": "UAT Northwind Logistics",
                  "email": self.state["lead_email"]},
            headers=self.auth(),
        )
        expect(duplicate.status_code == 409,
               f"expected 409 for duplicate e-mail, got {duplicate.status_code}")
        check = self.client.post(
            "/api/v1/leads/duplicate-check",
            json={"email": self.state["lead_email"]},
            headers=self.auth(),
        )
        expect(check.status_code == 200, f"duplicate-check returned {check.status_code}")
        body = check.json()
        expect(body.get("is_duplicate") is True, f"is_duplicate not true: {body}")
        self.note(r, f"duplicate-check={json.dumps(body, sort_keys=True)}")

    def uat_07_list_and_pagination(self, r: Result) -> None:
        response = self.client.get(
            "/api/v1/leads", params={"page": 1, "page_size": 5}, headers=self.auth()
        )
        expect(response.status_code == 200, f"expected 200, got {response.status_code}")
        rows = response.json()
        expect(isinstance(rows, list), "GET /leads must return a bare JSON array")
        expect("x-total-count" in {k.lower() for k in response.headers},
               "missing X-Total-Count header")
        expect(len(rows) <= 5, f"page_size ignored: {len(rows)} rows")
        self.note(r, f"X-Total-Count={response.headers.get('x-total-count')} "
                     f"X-Page={response.headers.get('x-page')} "
                     f"X-Page-Size={response.headers.get('x-page-size')}")

        search = self.client.get(
            "/api/v1/leads", params={"query": "Northwind"}, headers=self.auth()
        )
        expect(search.status_code == 200, f"search returned {search.status_code}")
        expect(any(row.get("id") == self.state["lead_id"] for row in search.json()),
               "search did not return the created lead")
        self.note(r, f"search returned {len(search.json())} row(s)")

    def uat_08_update_stage(self, r: Result) -> None:
        lead_id = self.state["lead_id"]
        response = self.client.patch(
            f"/api/v1/leads/{lead_id}",
            json={"stage": "proposal", "pain_points": "Manual dispatch planning"},
            headers=self.auth(),
        )
        expect(response.status_code == 200,
               f"expected 200, got {response.status_code}: {response.text[:200]}")
        body = response.json()
        expect(body.get("stage") == "proposal", f"stage not updated: {body.get('stage')!r}")
        self.note(r, f"stage={body.get('stage')} status={body.get('status')}")

    def uat_09_csv_import(self, r: Result) -> None:
        s = self.state.get("suffix", "")
        csv = (
            "company_name,industry,contact_name,email,stage\n"
            f"UAT Contoso Manufacturing {s},Manufacturing,Lee Chan,lee.uat.{s}@contoso.example,prospecting\n"
            f"UAT Fabrikam Retail {s},Retail,Priya Nair,priya.uat.{s}@fabrikam.example,discovery\n"
            f"UAT Duplicate Row {s},Retail,Ada Fernandes,{self.state['lead_email']},prospecting\n"
        )
        response = self.client.post(
            "/api/v1/leads/import",
            files={"file": ("uat-leads.csv", csv.encode("utf-8"), "text/csv")},
            headers=self.auth(),
        )
        expect(response.status_code == 200,
               f"expected 200, got {response.status_code}: {response.text[:300]}")
        report = response.json()
        expect(report.get("imported") == 2,
               f"expected 2 imported rows, got {report.get('imported')}")
        expect(report.get("duplicates") == 1,
               f"duplicate row not reported: {json.dumps(report)[:300]}")
        expect(report.get("total_rows") == 3,
               f"total_rows wrong: {report.get('total_rows')}")
        self.note(r, f"import report={json.dumps(report)[:400]}")

    def uat_10_invalid_lead(self, r: Result) -> None:
        response = self.client.post(
            "/api/v1/leads",
            json={"company_name": "", "email": "not-an-email"},
            headers=self.auth(),
        )
        expect(response.status_code == 422,
               f"expected 422 for invalid input, got {response.status_code}")
        self.note(r, f"body={response.text[:200]}")

    def uat_11_intelligence(self, r: Result) -> None:
        lead_id = self.state["lead_id"]
        response = self.client.post(
            f"/api/v1/leads/{lead_id}/insights",
            json={"product_service": "Dispatch automation suite"},
            headers=self.auth(),
        )
        expect(response.status_code == 200,
               f"expected 200, got {response.status_code}: {response.text[:300]}")
        body = response.json()
        for key in ("company_overview", "possible_needs", "opportunities",
                    "qualification", "missing_information"):
            expect(key in body, f"intelligence output missing {key!r}")
        expect(isinstance(body.get("possible_needs"), list) and body["possible_needs"],
               "possible_needs must be a non-empty list")
        expect(isinstance(body.get("missing_information"), list),
               "missing_information must be a list")
        self.note(r, f"provider={body.get('execution', {}).get('provider')} "
                     f"needs={len(body['possible_needs'])} "
                     f"opportunities={len(body.get('opportunities') or [])}")

        stored = self.client.get(f"/api/v1/leads/{lead_id}/insights", headers=self.auth())
        expect(stored.status_code == 200, f"insight read-back returned {stored.status_code}")
        expect(len(stored.json()) >= 1, "intelligence was not persisted")
        self.note(r, f"persisted insight rows={len(stored.json())}")

    def uat_12_outreach(self, r: Result) -> None:
        lead_id = self.state["lead_id"]
        response = self.client.post(
            "/api/v1/outreach/generate",
            json={
                "lead_id": lead_id,
                "tone": "consultative",
                "length": "short",
                "outreach_type": "cold_email",
                "goal": "book a 20 minute discovery call",
                "industry": "Logistics",
                "pain_points": ["manual dispatch planning", "driver turnover"],
            },
            headers=self.auth(),
        )
        expect(response.status_code == 200,
               f"expected 200, got {response.status_code}: {response.text[:300]}")
        draft = response.json()
        expect(bool(draft.get("body")), "generated body is empty")
        expect(bool(draft.get("subject_line")), "generated subject line is empty")
        campaign_id = draft.get("id")
        expect(bool(campaign_id), "campaign id missing from generate response")
        self.state["campaign_id"] = campaign_id
        self.note(r, f"campaign id={campaign_id} channel={draft.get('channel')} "
                     f"body_chars={len(draft['body'])}")

        edited = self.client.patch(
            f"/api/v1/outreach/campaigns/{campaign_id}",
            json={"body": (draft["body"] + "\n\n[edited by QA]").strip(),
                  "subject": draft["subject_line"]},
            headers=self.auth(),
        )
        expect(edited.status_code == 200,
               f"edit returned {edited.status_code}: {edited.text[:200]}")
        self.note(r, "draft edit accepted")

        history = self.client.get(
            f"/api/v1/leads/{lead_id}/outreach-drafts", headers=self.auth()
        )
        expect(history.status_code == 200, f"history returned {history.status_code}")
        expect(len(history.json()) >= 1, "outreach history is empty")
        self.note(r, f"history rows={len(history.json())}")

    def uat_13_send_disabled(self, r: Result) -> None:
        response = self.client.post("/api/v1/outreach/send", json={}, headers=self.auth())
        expect(response.status_code == 501,
               f"expected a visible 501, got {response.status_code}")
        body = response.json()
        expect(body.get("code") == "email_transport_not_configured",
               f"unexpected code: {body.get('code')!r}")
        self.note(r, f"code={body.get('code')} detail={str(body.get('detail'))[:160]}")

    def uat_14_scoring(self, r: Result) -> None:
        lead_id = self.state["lead_id"]
        response = self.client.post(f"/api/v1/leads/{lead_id}/scores", headers=self.auth())
        expect(response.status_code == 200,
               f"expected 200, got {response.status_code}: {response.text[:300]}")
        score = response.json()
        expect(isinstance(score.get("score"), int) and 0 <= score["score"] <= 100,
               f"score out of the agreed 0-100 scale: {score.get('score')!r}")
        expect("conversion_probability" in score, "conversion_probability field missing")
        expect(score["conversion_probability"] is None,
               "heuristic engine must not present a calibrated probability")
        factors = score.get("factors") or []
        names = {str(f.get("name", "")).lower() for f in factors}
        expect(len(factors) == 4, f"expected four scoring factors, got {len(factors)}")
        for expected in ("engagement", "fit", "intent", "decision readiness"):
            expect(any(expected in name for name in names),
                   f"factor {expected!r} missing from explanation: {names}")
        # Weights are expressed in score points (FR-030 / D-09 proposal: 0-100).
        total_weight = sum(float(f.get("weight", 0)) for f in factors)
        expect(abs(total_weight - 100) < 0.01,
               f"factor weights sum to {total_weight}, expected 100 points")
        recomputed = round(sum(float(f.get("points", 0)) for f in factors))
        expect(abs(recomputed - score["score"]) <= 1,
               f"score {score['score']} does not equal the sum of factor points {recomputed}")
        expect(bool(score.get("explanation")), "score has no explanation")
        self.note(r, f"score={score['score']} priority={score.get('priority_level')} "
                     f"probability={score['conversion_probability']} "
                     f"model={score.get('model_version')}")

        latest = self.client.get(
            f"/api/v1/leads/{lead_id}/scores/latest", headers=self.auth()
        )
        expect(latest.status_code == 200, f"latest score returned {latest.status_code}")
        self.note(r, f"latest score id={latest.json().get('id')}")

    def uat_15_recommendation(self, r: Result) -> None:
        lead_id = self.state["lead_id"]
        response = self.client.get(
            f"/api/v1/recommendations/{lead_id}", headers=self.auth()
        )
        expect(response.status_code == 200,
               f"expected 200, got {response.status_code}: {response.text[:300]}")
        body = response.json()
        for key in ("recommended_action", "reason", "priority", "suggested_timing",
                    "follow_up_draft"):
            expect(body.get(key) not in (None, ""),
                   f"recommendation is missing {key!r}: {json.dumps(body)[:300]}")
        self.note(r, f"priority={body.get('priority')} "
                     f"timing={body.get('suggested_timing')!r}")

        # FR-032 asks for follow-up timing, *channel* and content strategy.
        # Timing (suggested_timing) and content (follow_up_draft) are present;
        # no explicit channel field is returned. Recorded as BUG-006 rather
        # than silently accepted.
        channel_keys = [k for k in body if "channel" in k.lower()]
        if not channel_keys:
            r.status = "PARTIAL"
            r.detail = ("FR-032 partially met: timing and content are returned, "
                        "but no explicit channel field exists (BUG-006).")
            self.note(r, "deviation: response has no channel/channel_hint field")
        else:
            self.note(r, f"channel field(s) present: {channel_keys}")

    def uat_16_conversation(self, r: Result) -> None:
        lead_id = self.state["lead_id"]
        notes = (
            "Call with Ada Fernandes, 24 Oct 2026.\n"
            "Discussed dispatch backlog and driver turnover.\n"
            "Ada will send the current routing spreadsheet by Friday.\n"
            "We agreed to prepare a pilot proposal for 50 vehicles.\n"
        )
        response = self.client.post(
            "/api/v1/conversations/summarize",
            json={"lead_id": lead_id, "transcript": notes, "interaction_type": "call"},
            headers=self.auth(),
        )
        expect(response.status_code == 200,
               f"expected 200, got {response.status_code}: {response.text[:300]}")
        body = response.json()
        expect(bool(body.get("executive_summary")), "no executive summary produced")
        expect(isinstance(body.get("key_discussion_points"), list),
               "key_discussion_points must be a list")
        expect(isinstance(body.get("action_items"), list), "action_items must be a list")
        self.note(r, f"summary={str(body.get('executive_summary'))[:120]!r} "
                     f"points={len(body.get('key_discussion_points') or [])} "
                     f"actions={len(body.get('action_items') or [])}")

        stored = self.client.get(
            f"/api/v1/leads/{lead_id}/conversations", headers=self.auth()
        )
        expect(stored.status_code == 200, f"conversation list returned {stored.status_code}")
        expect(len(stored.json()) >= 1, "interaction was not stored")
        self.note(r, f"stored interactions={len(stored.json())}")

    def uat_17_crm_sync(self, r: Result) -> None:
        lead_id = self.state["lead_id"]
        before = self.client.get("/api/v1/crm/sync-logs", headers=self.auth())
        expect(before.status_code == 200, f"sync-logs returned {before.status_code}")
        before_count = len(before.json())

        response = self.client.post(
            "/api/v1/crm/sync",
            json={"provider": "salesforce", "lead_ids": [lead_id]},
            headers=self.auth(),
        )
        expect(response.status_code == 501,
               f"expected a visible 501, got {response.status_code}")
        body = response.json()
        expect(body.get("code") == "crm_not_configured",
               f"unexpected code: {body.get('code')!r}")
        self.note(r, f"code={body.get('code')} meta={body.get('meta')}")

        after = self.client.get("/api/v1/crm/sync-logs", headers=self.auth())
        expect(after.status_code == 200, f"sync-logs returned {after.status_code}")
        expect(len(after.json()) == before_count + 1,
               "failed sync attempt was not recorded in the sync log")
        self.note(r, f"sync log rows {before_count} -> {len(after.json())}")

        lead = self.client.get(f"/api/v1/leads/{lead_id}", headers=self.auth())
        expect(lead.status_code == 200,
               "local lead disappeared after a failed CRM sync")

    def uat_18_analytics(self, r: Result) -> None:
        response = self.client.get("/api/v1/analytics", headers=self.auth())
        expect(response.status_code == 200,
               f"expected 200, got {response.status_code}: {response.text[:300]}")
        body = response.json()
        for key in ("total_leads", "conversion_rate", "pipeline_value",
                    "average_response_time_days", "average_sales_cycle_days",
                    "pipeline_distribution"):
            expect(key in body, f"analytics missing {key!r}")
        expect(isinstance(body["total_leads"], int) and body["total_leads"] >= 3,
               f"total_leads looks wrong: {body['total_leads']!r}")
        expect(body["conversion_rate"]["value"] is not None,
               "conversion_rate must be computed (D-10 proposal)")
        for key in ("pipeline_value", "average_response_time_days",
                    "average_sales_cycle_days"):
            metric = body[key]
            expect(metric.get("value") is None,
                   f"{key} must not invent a number while D-10 is open")
            expect(metric.get("pending_definition") is True,
                   f"{key} must be flagged pending_definition")
        self.note(r, f"total_leads={body['total_leads']} "
                     f"conversion_rate={body['conversion_rate']['value']} "
                     f"pipeline_value={body['pipeline_value']['value']} "
                     f"pending={body['pipeline_value']['pending_definition']}")

    def uat_19_follow_ups(self, r: Result) -> None:
        response = self.client.get("/api/v1/follow-ups", headers=self.auth())
        expect(response.status_code == 200,
               f"expected 200, got {response.status_code}: {response.text[:200]}")
        rows = response.json()
        expect(isinstance(rows, list), "follow-ups must return a list")
        if rows:
            first = rows[0]
            for key in ("lead_id", "company_name", "priority",
                        "recommended_action", "reason"):
                expect(key in first, f"follow-up row missing {key!r}")
            self.note(r, f"rows={len(rows)} first_priority={first.get('priority')}")
        else:
            self.note(r, "rows=0 (no scored, non-terminal leads)")

    def uat_20_rbac(self, r: Result) -> None:
        suffix = datetime.now(timezone.utc).strftime("%H%M%S")
        viewer_email = f"qa.viewer.{suffix}@example.com"
        viewer_password = "UatViewerPass123!"
        created = self.client.post(
            "/api/v1/auth/users",
            json={"email": viewer_email, "full_name": "QA Viewer",
                  "password": viewer_password, "role": "viewer"},
            headers=self.auth(),
        )
        expect(created.status_code == 201,
               f"admin could not create a user: {created.status_code} {created.text[:200]}")
        self.note(r, f"created viewer id={created.json().get('id')}")

        viewer_token = self.login(viewer_email, viewer_password)
        expect(viewer_token.status_code == 200,
               f"new user could not log in: {viewer_token.status_code}")
        token = viewer_token.json()["access_token"]

        denied = self.client.post(
            "/api/v1/leads",
            json={"company_name": "UAT Should Not Exist"},
            headers=self.auth(token),
        )
        expect(denied.status_code == 403,
               f"viewer write should be 403, got {denied.status_code}")
        self.note(r, f"viewer write denied with {denied.status_code}")

        readable = self.client.get("/api/v1/leads", headers=self.auth(token))
        expect(readable.status_code == 200,
               f"viewer read should be allowed, got {readable.status_code}")
        self.note(r, "viewer read allowed")

        admin_only = self.client.get("/api/v1/auth/users", headers=self.auth(token))
        expect(admin_only.status_code == 403,
               f"viewer user administration should be 403, got {admin_only.status_code}")
        self.note(r, "viewer user administration denied")

    def uat_21_delete(self, r: Result) -> None:
        lead_id = self.state["lead_id"]
        response = self.client.delete(f"/api/v1/leads/{lead_id}", headers=self.auth())
        expect(response.status_code == 204,
               f"expected 204, got {response.status_code}: {response.text[:200]}")
        gone = self.client.get(f"/api/v1/leads/{lead_id}", headers=self.auth())
        expect(gone.status_code == 404, f"deleted lead still readable: {gone.status_code}")
        self.note(r, "delete returned 204 and the record is gone")

    # -- driver -----------------------------------------------------------
    def execute(self) -> None:
        workflows = [
            ("UAT-01", "Health and readiness", "NFR-011", self.uat_01_health),
            ("UAT-02", "Administrator can sign in", "FR-001 / D-04", self.uat_02_login),
            ("UAT-03", "Wrong password is refused", "NFR-005", self.uat_03_bad_password),
            ("UAT-04", "Unauthenticated access is refused", "NFR-005", self.uat_04_unauthenticated),
            ("UAT-05", "Create a prospect manually", "FR-001, FR-009", self.uat_05_create_lead),
            ("UAT-06", "Duplicate detection", "FR-008", self.uat_06_duplicates),
            ("UAT-07", "List, search and paginate prospects", "FR-002", self.uat_07_list_and_pagination),
            ("UAT-08", "Move a prospect between lifecycle stages", "FR-005", self.uat_08_update_stage),
            ("UAT-09", "Import prospects from CSV", "FR-007, FR-008", self.uat_09_csv_import),
            ("UAT-10", "Invalid input is rejected cleanly", "AC-005", self.uat_10_invalid_lead),
            ("UAT-11", "Company intelligence is generated and stored", "FR-011..FR-016", self.uat_11_intelligence),
            ("UAT-12", "Outreach is generated, edited and retrieved", "FR-019..FR-026", self.uat_12_outreach),
            ("UAT-13", "Send is visibly unavailable, not faked", "FR-024 / D-05", self.uat_13_send_disabled),
            ("UAT-14", "Lead score is explainable and honest", "FR-028..FR-031", self.uat_14_scoring),
            ("UAT-15", "Next-best-action recommendation", "FR-032", self.uat_15_recommendation),
            ("UAT-16", "Conversation notes are summarised and stored", "FR-036..FR-039", self.uat_16_conversation),
            ("UAT-17", "CRM sync fails safely and is logged", "FR-043, FR-045", self.uat_17_crm_sync),
            ("UAT-18", "Dashboard KPIs are computed or honestly withheld", "FR-046..FR-050", self.uat_18_analytics),
            ("UAT-19", "Follow-up panel data", "FR-052", self.uat_19_follow_ups),
            ("UAT-20", "Role-based access control", "NFR-005", self.uat_20_rbac),
            ("UAT-21", "Delete a prospect", "FR-004", self.uat_21_delete),
        ]
        for result_id, title, requirement, fn in workflows:
            self.run(result_id, title, requirement, fn)

    def report(self) -> str:
        passed = sum(1 for r in self.results if r.status == "PASS")
        partial = sum(1 for r in self.results if r.status == "PARTIAL")
        failed = len(self.results) - passed - partial
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines = [
            "# Live UAT run",
            "",
            f"- **Executed:** {stamp}",
            f"- **Target:** `{self.base_url}`",
            f"- **Operator:** `{self.email}`",
            f"- **Workflows:** {len(self.results)}",
            f"- **Result:** {passed} passed, {partial} partial, {failed} failed",
            "",
            "| ID | Workflow | Requirement | Status | ms |",
            "|---|---|---|---|---|",
        ]
        for r in self.results:
            lines.append(
                f"| {r.id} | {r.title} | {r.requirement} | **{r.status}** | {r.duration_ms} |"
            )
        lines += ["", "## Detail", ""]
        for r in self.results:
            lines.append(f"### {r.id} - {r.title} ({r.status})")
            lines.append("")
            if r.detail:
                lines.append(f"- Failure: `{r.detail}`")
            for item in r.evidence:
                lines.append(f"- {item}")
            if not r.detail and not r.evidence:
                lines.append("- No additional evidence captured.")
            lines.append("")
        return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("UAT_BASE_URL", "http://127.0.0.1:8011"))
    parser.add_argument("--email", default=os.getenv("UAT_EMAIL", ""))
    parser.add_argument("--password", default=os.getenv("UAT_PASSWORD", ""))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--label", default="")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)

    if not args.email or not args.password:
        print("Provide --email/--password or set UAT_EMAIL/UAT_PASSWORD.")
        return 2

    runner = Runner(args.base_url, args.email, args.password)
    try:
        runner.client.get("/api/v1/health")
    except httpx.HTTPError as exc:
        print(f"Cannot reach {args.base_url}: {exc.__class__.__name__}: {exc}")
        print("Start the API first; see docs/qa/uat-plan.md.")
        return 2

    runner.execute()

    passed = sum(1 for r in runner.results if r.status == "PASS")
    partial = sum(1 for r in runner.results if r.status == "PARTIAL")
    failed = len(runner.results) - passed - partial
    print(f"\n{passed}/{len(runner.results)} workflows passed"
          + (f", {partial} partial" if partial else "")
          + (f", {failed} failed" if failed else ""))

    if not args.no_write:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        suffix = f"-{args.label}" if args.label else ""
        md_path = out_dir / f"{stamp}-uat-live{suffix}.md"
        json_path = out_dir / f"{stamp}-uat-live{suffix}.json"
        md_path.write_text(runner.report(), encoding="utf-8")
        json_path.write_text(
            json.dumps(
                {
                    "executed_at": datetime.now(timezone.utc).isoformat(),
                    "base_url": args.base_url,
                    "operator": args.email,
                    "passed": passed,
                    "partial": partial,
                    "failed": failed,
                    "results": [asdict(r) for r in runner.results],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"Wrote {md_path}")
        print(f"Wrote {json_path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
