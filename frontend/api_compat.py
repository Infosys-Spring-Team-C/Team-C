"""Compatibility layer between the submitted Streamlit UI and the Team-C API.

The UI was written against the contributor's own FastAPI backend.  Team-C's
canonical API uses different paths and payload shapes, so this module
translates both directions instead of changing the UI or adding legacy routes
to the backend:

* request paths and payloads are mapped onto ``/api/v1/...``;
* responses are normalised into the flat shapes the UI renders
  (``lead_id``, ``lead_score``, ``email_subject`` ...).

Nothing here performs AI work, reads the database or invents data.  A missing
value stays missing (``None``) so the UI can say so.

Configuration (environment variables):

``SALES_GENIE_BACKEND_BASE_URL``
    API root, for example ``http://127.0.0.1:8000``.
``SALES_GENIE_BACKEND_TOKEN``
    Optional bearer token.  If unset, ``SALES_GENIE_BACKEND_EMAIL`` and
    ``SALES_GENIE_BACKEND_PASSWORD`` are used once to obtain a token.
"""
from __future__ import annotations

import csv
import io
import os
import re
from typing import Any

import requests

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT = 8.0

_TOKEN: str | None = None

#: The UI's pipeline labels -> the canonical lifecycle stage.
_STATUS_TO_STAGE = {
    "new": "prospecting",
    "prospecting": "prospecting",
    "contacted": "discovery",
    "discovery": "discovery",
    "qualified": "qualified",
    "proposal": "proposal",
    "proposal sent": "proposal",
    "negotiation": "negotiation",
    "converted": "converted",
    "won": "converted",
    "lost": "lost",
}


# ---------------------------------------------------------------------------
# Configuration and transport
# ---------------------------------------------------------------------------
def resolve_base_url() -> str:
    """API root from the environment, with a local-development default."""
    for name in ("SALES_GENIE_BACKEND_BASE_URL", "BACKEND_URL"):
        value = os.getenv(name, "").strip()
        if value:
            return value.rstrip("/")
    return DEFAULT_BASE_URL


def _token(base_url: str, timeout: float) -> str | None:
    """Bearer token from the environment, or a one-off login."""
    global _TOKEN
    if _TOKEN:
        return _TOKEN

    configured = os.getenv("SALES_GENIE_BACKEND_TOKEN", "").strip()
    if configured:
        _TOKEN = configured
        return _TOKEN

    email = os.getenv("SALES_GENIE_BACKEND_EMAIL", "").strip()
    password = os.getenv("SALES_GENIE_BACKEND_PASSWORD", "")
    if not (email and password):
        return None

    try:
        response = requests.post(
            f"{base_url}/api/v1/auth/token",
            data={"username": email, "password": password},
            timeout=timeout,
        )
    except requests.RequestException:
        return None
    if response.status_code != 200:
        return None
    _TOKEN = (response.json() or {}).get("access_token")
    return _TOKEN


def _detail(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return (response.text or "").strip()[:300]
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, dict):
            return str(detail.get("message") or detail.get("code") or detail)
        if detail:
            return str(detail)
    return str(payload)[:300]


def _request(
    method: str,
    base_url: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_data: Any = None,
    files: dict[str, Any] | None = None,
    timeout: float | None = None,
) -> tuple[bool, Any]:
    base = base_url.rstrip("/")
    request_timeout = DEFAULT_TIMEOUT if timeout is None else timeout
    headers: dict[str, str] = {}
    token = _token(base, request_timeout)
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.request(
            method,
            f"{base}{path}",
            params=params,
            json=json_data,
            files=files,
            headers=headers,
            timeout=request_timeout,
        )
    except requests.exceptions.ConnectionError:
        return False, {
            "error": "Cannot connect to the backend server.",
            "connection_error": True,
        }
    except requests.exceptions.Timeout:
        return False, {"error": "The backend did not respond in time.", "timeout": True}
    except Exception as exc:  # noqa: BLE001 - surfaced to the UI as text
        return False, {"error": str(exc)}

    if response.status_code in (200, 201):
        try:
            return True, response.json()
        except ValueError:
            return True, {}

    if response.status_code == 404:
        return False, {"error": "Resource not found (404)", "status_code": 404}

    message = _detail(response)
    if response.status_code == 401:
        message = (
            "Authentication required. Set SALES_GENIE_BACKEND_TOKEN, or "
            "SALES_GENIE_BACKEND_EMAIL and SALES_GENIE_BACKEND_PASSWORD, or run "
            "the API with AUTH_ENABLED=false for a local demo."
        )
    return False, {
        "error": f"Server HTTP {response.status_code}: {message}",
        "status_code": response.status_code,
        "message": message,
    }


# ---------------------------------------------------------------------------
# Response normalisation (pure functions, unit-tested without a server)
# ---------------------------------------------------------------------------
def normalise_lead(raw: dict[str, Any]) -> dict[str, Any]:
    """Team-C ``LeadRead`` -> the flat record the UI renders."""
    return {
        "lead_id": raw.get("id"),
        "company_name": raw.get("company_name", ""),
        "industry": raw.get("industry", ""),
        "contact_name": raw.get("contact_name", ""),
        "email": raw.get("email", ""),
        "phone": raw.get("phone", ""),
        "company_size": raw.get("company_size", ""),
        "funding_stage": raw.get("funding_stage", ""),
        "business_need": raw.get("explicit_needs", ""),
        "lead_status": raw.get("status") or raw.get("stage", ""),
        "company_description": raw.get("company_description", ""),
        "prospect_role": raw.get("prospect_role", ""),
        "engagement_history": raw.get("engagement_history", ""),
        "response_behavior": raw.get("response_behavior", ""),
        "user_research": raw.get("user_research", ""),
    }


def lead_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """UI create form -> ``LeadCreate``."""
    body = {
        "company_name": payload.get("company_name", ""),
        "industry": payload.get("industry", ""),
        "contact_name": payload.get("contact_name", ""),
        "email": payload.get("email", ""),
        "phone": payload.get("phone", ""),
        "company_size": payload.get("company_size", ""),
        "funding_stage": payload.get("funding_stage", ""),
        "explicit_needs": payload.get("business_need", ""),
    }
    stage = _STATUS_TO_STAGE.get(str(payload.get("lead_status", "")).strip().lower())
    if stage:
        body["stage"] = stage
    return body


def normalise_score(raw: dict[str, Any]) -> dict[str, Any]:
    """Team-C score record -> the flat score card the UI renders."""
    factors = raw.get("factors") or []
    labels: list[str] = []
    for factor in factors:
        name = str(factor.get("name", "")).strip()
        dimension = factor.get("dimension")
        if name and dimension and dimension != name:
            labels.append(f"{name} ({dimension})")
        elif name:
            labels.append(name)

    return {
        "lead_id": raw.get("lead_id"),
        "lead_score": raw.get("score", 0),
        "priority_level": raw.get("priority_level", ""),
        "conversion_probability": raw.get("conversion_probability"),
        "reason": raw.get("explanation") or raw.get("methodology_note") or "",
        "next_action": raw.get("recommended_next_action", ""),
        "scoring_factors": labels,
        "positive_signals": raw.get("positive_signals", []),
        "negative_signals": raw.get("negative_signals", []),
        "missing_information": raw.get("missing_information", []),
    }


def _join_statements(items: Any) -> str:
    parts: list[str] = []
    for item in items or []:
        if isinstance(item, dict):
            text = str(item.get("statement", "")).strip()
        else:
            text = str(item).strip()
        if text:
            parts.append(text)
    return "; ".join(parts)


def normalise_insight(raw: dict[str, Any]) -> dict[str, Any]:
    """Team-C lead intelligence -> the three cards the UI renders.

    Two shapes exist and both are supported:

    * ``POST /leads/{id}/insights`` returns a flat ``LeadIntelligence``
      (``company_overview``, ``possible_needs`` ...);
    * ``GET /leads/{id}/insights`` returns a list of persisted rows, where the
      same data is stored under ``industry_context`` / ``business_needs``.
    """
    # Flat LeadIntelligence (POST) or a persisted row (GET list item).
    needs_source = raw.get("possible_needs")
    if needs_source is None:
        needs_source = raw.get("business_needs")
    opportunities_source = raw.get("opportunities")
    overview = raw.get("company_overview") or raw.get("industry_context") or ""
    fit = raw.get("product_industry_fit") or raw.get("recommended_value_proposition") or ""
    qualification = raw.get("qualification") or {}
    if not isinstance(qualification, dict):
        qualification = {}

    needs = _join_statements(needs_source)
    opportunities = _join_statements(opportunities_source)
    return {
        "business_needs": needs
        or "No explicit need is recorded for this lead; confirm it in discovery.",
        "opportunities": opportunities
        or "No opportunity can be confirmed from the supplied context.",
        "industry_situation": overview
        or "No company overview is available from the supplied context.",
        "product_industry_fit": fit,
        "buyer_role_relevance": raw.get("buyer_role_relevance", ""),
        "discovery_questions": raw.get("discovery_questions", []),
        "missing_information": raw.get("missing_information", []),
        "qualification_category": qualification.get("category", ""),
        "confidence": raw.get("confidence") or qualification.get("confidence", "low"),
        "disclaimer": raw.get("disclaimer", ""),
    }


def normalise_draft(raw: dict[str, Any]) -> dict[str, Any]:
    """Team-C outreach draft -> the fields the email studio edits."""
    return {
        "email_subject": raw.get("subject_line") or raw.get("subject") or "",
        "email_content": raw.get("body") or "",
        "channel": raw.get("channel", ""),
        "call_to_action": raw.get("call_to_action", ""),
        "assumptions": raw.get("assumptions", []),
        "missing_context": raw.get("missing_context", []),
    }


def normalise_analytics(raw: dict[str, Any], leads: list[dict[str, Any]]) -> dict[str, Any]:
    """Team-C ``AnalyticsResponse`` -> the dashboard KPI shape."""
    bands = {
        str(item.get("band", "")): int(item.get("count", 0) or 0)
        for item in raw.get("lead_score_distribution") or []
        if isinstance(item, dict)
    }
    conversion = (raw.get("conversion_rate") or {}).get("value")
    industries: dict[str, int] = {}
    for lead in leads:
        key = str(lead.get("industry") or "Unknown").strip() or "Unknown"
        industries[key] = industries.get(key, 0) + 1

    return {
        "total_leads": raw.get("total_leads", len(leads)),
        "hot_leads": bands.get("70-100", 0),
        "warm_leads": bands.get("45-69", 0),
        "cold_leads": bands.get("0-44", 0),
        "emails_generated": raw.get("outreach_activity", 0),
        # No delivery transport exists (SRS D-05), so nothing has been sent.
        "emails_sent": 0,
        "calls_done": raw.get("interactions_logged", 0),
        "conversion_rate": round(conversion * 100, 1) if conversion is not None else 0.0,
        "industry_distribution": industries,
        "average_lead_score": raw.get("average_lead_score"),
        "is_demo": raw.get("is_demo", False),
    }


def records_to_csv(records: list[dict[str, Any]]) -> bytes:
    """UI bulk-import records -> the CSV Team-C's importer expects."""
    buffer = io.StringIO()
    fieldnames = [
        "company_name",
        "industry",
        "contact_name",
        "email",
        "phone",
        "company_size",
        "business_need",
        "status",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for record in records:
        row = dict(record)
        stage = _STATUS_TO_STAGE.get(str(row.get("lead_status", "")).strip().lower())
        row["status"] = stage or "prospecting"
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


# ---------------------------------------------------------------------------
# Endpoint translation
# ---------------------------------------------------------------------------
_LEAD_ID = r"(?P<lead_id>\d+)"


def api_get(
    base_url: str, endpoint: str, params: dict[str, Any] | None = None, timeout: float | None = None
) -> tuple[bool, Any]:
    """Drop-in replacement for the UI's original ``api_get``."""
    base = base_url.rstrip("/")
    path = "/" + endpoint.lstrip("/")

    if path.rstrip("/") in ("/health",):
        return _request("GET", base, "/health", params=params, timeout=timeout)

    if re.fullmatch(r"/leads/?", path):
        query = {"page_size": 500}
        if params:
            query.update(params)
        ok, data = _request("GET", base, "/api/v1/leads", params=query, timeout=timeout)
        if not ok:
            return ok, data
        items = data if isinstance(data, list) else data.get("items", [])
        return True, [normalise_lead(item) for item in items]

    match = re.fullmatch(rf"/intelligence/analyze/{_LEAD_ID}/?", path)
    if match:
        ok, data = _request(
            "GET", base, f"/api/v1/leads/{match.group('lead_id')}/insights", timeout=timeout
        )
        if not ok:
            return ok, data
        # The canonical endpoint returns the saved analyses, newest first.
        rows = data if isinstance(data, list) else [data]
        if not rows:
            return False, {
                "error": "No saved analysis for this lead. Generate one first.",
                "status_code": 404,
            }
        return True, normalise_insight(rows[0])

    match = re.fullmatch(rf"/intelligence/score/{_LEAD_ID}/?", path)
    if match:
        ok, data = _request(
            "GET",
            base,
            f"/api/v1/leads/{match.group('lead_id')}/scores/latest",
            timeout=timeout,
        )
        return (True, normalise_score(data)) if ok else (ok, data)

    match = re.fullmatch(rf"/intelligence/outreach/{_LEAD_ID}/?", path)
    if match:
        ok, data = _request(
            "GET",
            base,
            f"/api/v1/leads/{match.group('lead_id')}/outreach-drafts",
            timeout=timeout,
        )
        if not ok:
            return ok, data
        drafts = data if isinstance(data, list) else []
        if not drafts:
            return False, {"error": "No saved outreach draft for this lead.", "status_code": 404}
        # The canonical endpoint returns drafts newest first.
        return True, normalise_draft(drafts[0])

    if re.fullmatch(r"/analytics/dashboard/?", path):
        ok, data = _request("GET", base, "/api/v1/analytics", timeout=timeout)
        if not ok:
            return ok, data
        leads_ok, leads = api_get(base, "/leads/", timeout=timeout)
        return True, normalise_analytics(data, leads if leads_ok else [])

    return _request("GET", base, path, params=params, timeout=timeout)


def api_post(
    base_url: str, endpoint: str, json_data: Any = None, timeout: float | None = None
) -> tuple[bool, Any]:
    """Drop-in replacement for the UI's original ``api_post``."""
    base = base_url.rstrip("/")
    path = "/" + endpoint.lstrip("/")

    if re.fullmatch(r"/leads/?", path):
        ok, data = _request(
            "POST", base, "/api/v1/leads", json_data=lead_payload(json_data or {}), timeout=timeout
        )
        if not ok:
            return ok, data
        return True, {"message": "Lead added successfully.", "lead": normalise_lead(data)}

    if re.fullmatch(r"/leads/bulk/?", path):
        records = json_data if isinstance(json_data, list) else []
        if not records:
            return False, {"error": "No records to import."}
        files = {"file": ("leads.csv", records_to_csv(records), "text/csv")}
        ok, data = _request(
            "POST", base, "/api/v1/leads/import", files=files, timeout=timeout
        )
        if not ok:
            return ok, data
        message = (
            f"{data.get('imported', 0)} imported, "
            f"{data.get('duplicates', 0)} duplicates, "
            f"{data.get('invalid', 0)} invalid."
        )
        return True, {"message": message, "report": data}

    match = re.fullmatch(rf"/intelligence/analyze/{_LEAD_ID}/?", path)
    if match:
        ok, data = _request(
            "POST",
            base,
            f"/api/v1/leads/{match.group('lead_id')}/insights",
            timeout=timeout,
        )
        return (True, normalise_insight(data)) if ok else (ok, data)

    match = re.fullmatch(rf"/intelligence/score/{_LEAD_ID}/?", path)
    if match:
        ok, data = _request(
            "POST", base, f"/api/v1/leads/{match.group('lead_id')}/scores", timeout=timeout
        )
        return (True, normalise_score(data)) if ok else (ok, data)

    if re.fullmatch(r"/intelligence/outreach/?", path):
        body = dict(json_data or {})
        ok, data = _request(
            "POST", base, "/api/v1/outreach/generate", json_data=body, timeout=timeout
        )
        return (True, normalise_draft(data)) if ok else (ok, data)

    if re.fullmatch(r"/outreach/send-email/?", path):
        ok, data = _request("POST", base, "/api/v1/outreach/send", timeout=timeout)
        if ok:
            return True, {"configured": False, "success": False, "message": "Unexpected response."}
        message = data.get("message") or data.get("error") or "E-mail delivery is not configured."
        return False, {"configured": False, "success": False, "message": message, **data}

    return _request("POST", base, path, json_data=json_data, timeout=timeout)
