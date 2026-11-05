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


def login(base_url: str, email: str, password: str, timeout: float = DEFAULT_TIMEOUT) -> tuple[bool, str]:
    """Exchange credentials for a bearer token and keep it for this process.

    Used by the UI's sign-in form.  Credentials are never stored; only the
    token is kept in memory.
    """
    global _TOKEN
    base = base_url.rstrip("/")
    try:
        response = requests.post(
            f"{base}/api/v1/auth/token",
            data={"username": email, "password": password},
            timeout=timeout,
        )
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to the backend server."
    except requests.exceptions.Timeout:
        return False, "The backend did not respond in time."
    except Exception as exc:  # noqa: BLE001 - surfaced to the UI as text
        return False, str(exc)

    if response.status_code != 200:
        return False, _detail(response) or "Sign-in failed."
    token = (response.json() or {}).get("access_token")
    if not token:
        return False, "The backend returned no access token."
    _TOKEN = token
    return True, ""


def clear_token() -> None:
    """Forget the in-memory bearer token (sign-out)."""
    global _TOKEN
    _TOKEN = None


def has_token() -> bool:
    return bool(_TOKEN)


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
        "pain_points": raw.get("pain_points", ""),
        "annual_revenue": raw.get("annual_revenue", ""),
        "website": raw.get("website", ""),
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

    detail = []
    dimensions: dict[str, int] = {}
    for factor in factors:
        if not isinstance(factor, dict):
            continue
        detail.append(
            {
                "name": str(factor.get("name", "")).strip(),
                "dimension": factor.get("dimension") or "",
                "weight": factor.get("weight"),
                "value": factor.get("normalized_value"),
                "points": factor.get("points"),
                "signal": factor.get("signal") or "",
                "explanation": factor.get("explanation") or "",
            }
        )
        dimension = factor.get("dimension")
        if dimension:
            try:
                dimensions[str(dimension)] = int(
                    round(float(factor.get("normalized_value", 0)) * 100)
                )
            except (TypeError, ValueError):
                continue

    return {
        "lead_id": raw.get("lead_id"),
        "lead_score": raw.get("score", 0),
        "priority_level": raw.get("priority_level", ""),
        "category": raw.get("qualification_category", ""),
        "conversion_probability": raw.get("conversion_probability"),
        "probability_band": raw.get("probability_band"),
        "probability_note": raw.get("probability_note", ""),
        "methodology_note": raw.get("methodology_note", ""),
        "reason": raw.get("explanation") or raw.get("methodology_note") or "",
        "next_action": raw.get("recommended_next_action", ""),
        "scoring_factors": labels,
        "factors_detail": detail,
        "dimensions": dimensions,
        "positive_signals": raw.get("positive_signals", []),
        "negative_signals": raw.get("negative_signals", []),
        "missing_information": raw.get("missing_information", []),
        "model_version": raw.get("model_version", ""),
        "created_at": raw.get("created_at", ""),
        "execution": raw.get("execution") or {},
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

    def _statements(items: Any) -> list[str]:
        values: list[str] = []
        for item in items or []:
            text = (
                str(item.get("statement", "")).strip()
                if isinstance(item, dict)
                else str(item).strip()
            )
            if text:
                values.append(text)
        return values

    return {
        "business_needs": needs
        or "No explicit need is recorded for this lead; confirm it in discovery.",
        "opportunities": opportunities
        or "No opportunity can be confirmed from the supplied context.",
        "industry_situation": overview
        or "No company overview is available from the supplied context.",
        "product_industry_fit": fit,
        "buyer_role_relevance": raw.get("buyer_role_relevance", ""),
        "supported_facts": _statements(raw.get("supported_facts")),
        "potential_challenges": _statements(raw.get("potential_challenges")),
        "needs_detail": _statements(needs_source),
        "opportunities_detail": _statements(opportunities_source),
        "discovery_questions": raw.get("discovery_questions", []),
        "missing_information": raw.get("missing_information", []),
        "qualification_category": qualification.get("category", ""),
        "confidence": raw.get("confidence") or qualification.get("confidence", "low"),
        "disclaimer": raw.get("disclaimer", ""),
    }


def normalise_draft(raw: dict[str, Any]) -> dict[str, Any]:
    """Team-C outreach draft -> the fields the email studio edits."""
    return {
        "id": raw.get("id"),
        "status": raw.get("status", "draft"),
        "email_subject": raw.get("subject_line") or raw.get("subject") or "",
        "email_content": raw.get("body") or "",
        "channel": raw.get("channel", ""),
        "tone": raw.get("tone", ""),
        "call_to_action": raw.get("call_to_action", ""),
        "assumptions": raw.get("assumptions", []),
        "missing_context": raw.get("missing_context", []),
        "execution": raw.get("execution") or {},
        "created_at": raw.get("created_at", ""),
    }


def normalise_analytics(raw: dict[str, Any], leads: list[dict[str, Any]]) -> dict[str, Any]:
    """Team-C ``AnalyticsResponse`` -> the dashboard KPI shape."""
    bands = {
        str(item.get("band", "")): int(item.get("count", 0) or 0)
        for item in raw.get("lead_score_distribution") or []
        if isinstance(item, dict)
    }
    conversion = (raw.get("conversion_rate") or {}).get("value")
    pipeline_metric = raw.get("pipeline_value") or {}
    industries: dict[str, int] = {}
    for lead in leads:
        key = str(lead.get("industry") or "Unknown").strip() or "Unknown"
        industries[key] = industries.get(key, 0) + 1

    return {
        "total_leads": raw.get("total_leads", len(leads)),
        "qualified_leads": raw.get("qualified_leads", 0),
        "converted_leads": raw.get("converted_leads", 0),
        "hot_leads": bands.get("70-100", 0),
        "warm_leads": bands.get("45-69", 0),
        "cold_leads": bands.get("0-44", 0),
        "emails_generated": raw.get("outreach_activity", 0),
        # No delivery transport exists (SRS D-05), so nothing has been sent.
        "emails_sent": 0,
        "calls_done": raw.get("interactions_logged", 0),
        "conversion_rate": round(conversion * 100, 1) if conversion is not None else 0.0,
        "conversion_rate_defined": conversion is not None,
        "pipeline_value": pipeline_metric.get("value"),
        "pipeline_value_defined": (
            pipeline_metric.get("value") is not None
            and not pipeline_metric.get("pending_definition", False)
        ),
        "pipeline_distribution": raw.get("pipeline_distribution") or [],
        "activity_trend": raw.get("activity_trend") or [],
        "follow_up_tasks": raw.get("follow_up_tasks", 0),
        "industry_distribution": industries,
        "average_lead_score": raw.get("average_lead_score"),
        "is_demo": raw.get("is_demo", False),
        "source": raw.get("source", ""),
        "generated_at": raw.get("generated_at", ""),
    }


def normalise_conversation(raw: dict[str, Any]) -> dict[str, Any]:
    """Conversation summary (POST) or a stored interaction row (GET)."""
    return {
        "id": raw.get("id"),
        "lead_id": raw.get("lead_id"),
        "created_at": raw.get("created_at") or raw.get("interaction_date") or "",
        "interaction_type": raw.get("interaction_type", ""),
        "summary": raw.get("executive_summary") or raw.get("summary") or "",
        "key_points": raw.get("key_discussion_points") or raw.get("key_points") or [],
        "action_items": raw.get("action_items") or [],
        "requirements": raw.get("customer_requirements") or [],
        "pain_points": raw.get("pain_points") or [],
        "objections": raw.get("objections") or [],
        "buying_signals": raw.get("buying_signals") or [],
        "suggested_follow_up": raw.get("suggested_follow_up") or "",
        "missing": raw.get("missing_or_uncertain") or [],
    }


def normalise_follow_up(raw: dict[str, Any]) -> dict[str, Any]:
    """Follow-up item from ``GET /api/v1/follow-ups``."""
    return {
        "lead_id": str(raw.get("lead_id", "")),
        "company_name": raw.get("company_name", ""),
        "priority": raw.get("priority", ""),
        "action": raw.get("recommended_action", ""),
        "score": raw.get("score"),
        "last_interaction_at": raw.get("last_interaction_at") or "",
        "reason": raw.get("reason", ""),
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

    if re.fullmatch(r"/auth/me/?", path):
        return _request("GET", base, "/api/v1/auth/me", timeout=timeout)

    if re.fullmatch(r"/follow-ups/?", path):
        ok, data = _request("GET", base, "/api/v1/follow-ups", timeout=timeout)
        if not ok:
            return ok, data
        rows = data if isinstance(data, list) else []
        return True, [normalise_follow_up(item) for item in rows]

    match = re.fullmatch(rf"/recommendations/{_LEAD_ID}/?", path)
    if match:
        return _request(
            "GET",
            base,
            f"/api/v1/recommendations/{match.group('lead_id')}",
            timeout=timeout,
        )

    match = re.fullmatch(rf"/leads/{_LEAD_ID}/conversations/?", path)
    if match:
        ok, data = _request(
            "GET",
            base,
            f"/api/v1/leads/{match.group('lead_id')}/conversations",
            timeout=timeout,
        )
        if not ok:
            return ok, data
        rows = data if isinstance(data, list) else []
        return True, [normalise_conversation(item) for item in rows]

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

    # The canonical API stores drafts as outreach campaigns.  The UI exposes a
    # "save edits" action and a truthful "record as sent" action; neither sends
    # an email (SRS D-05).
    match = re.fullmatch(rf"/outreach/campaigns/(?P<campaign_id>\d+)/save/?", path)
    if match:
        ok, data = _request(
            "PATCH",
            base,
            f"/api/v1/outreach/campaigns/{match.group('campaign_id')}",
            json_data=json_data,
            timeout=timeout,
        )
        return (True, normalise_draft(data)) if ok else (ok, data)

    match = re.fullmatch(rf"/outreach/campaigns/(?P<campaign_id>\d+)/mark-sent/?", path)
    if match:
        ok, data = _request(
            "POST",
            base,
            f"/api/v1/outreach/campaigns/{match.group('campaign_id')}/mark-sent",
            json_data=json_data,
            timeout=timeout,
        )
        return (True, normalise_draft(data)) if ok else (ok, data)

    if re.fullmatch(r"/outreach/save/?", path):
        body = dict(json_data or {})
        lead_id = body.pop("lead_id", None)
        if not lead_id:
            return False, {"error": "lead_id is required to save a draft."}
        ok, data = _request(
            "POST",
            base,
            f"/api/v1/leads/{lead_id}/outreach-drafts",
            json_data=body,
            timeout=timeout,
        )
        return (True, normalise_draft(data)) if ok else (ok, data)

    if re.fullmatch(r"/outreach/send-email/?", path):
        ok, data = _request("POST", base, "/api/v1/outreach/send", timeout=timeout)
        if ok:
            return True, {"configured": False, "success": False, "message": "Unexpected response."}
        message = data.get("message") or data.get("error") or "E-mail delivery is not configured."
        return False, {"configured": False, "success": False, "message": message, **data}

    if re.fullmatch(r"/conversations/summarize/?", path):
        ok, data = _request(
            "POST",
            base,
            "/api/v1/conversations/summarize",
            json_data=json_data,
            timeout=timeout,
        )
        return (True, normalise_conversation(data)) if ok else (ok, data)

    if re.fullmatch(r"/analytics/insights/?", path):
        return _request(
            "POST",
            base,
            "/api/v1/analytics/insights",
            json_data=json_data or {},
            timeout=timeout,
        )

    return _request("POST", base, path, json_data=json_data, timeout=timeout)
