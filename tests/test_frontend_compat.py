"""Unit tests for the frontend compatibility layer.

These tests exercise the translation only: no server, no database and no AI
call. A fake transport records the request that would have been sent.
"""
from __future__ import annotations

import pytest

from frontend import api_compat


class FakeResponse:
    def __init__(self, status_code: int, payload=None, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


@pytest.fixture(autouse=True)
def _no_ambient_token(monkeypatch):
    for name in (
        "SALES_GENIE_BACKEND_TOKEN",
        "SALES_GENIE_BACKEND_EMAIL",
        "SALES_GENIE_BACKEND_PASSWORD",
        "SALES_GENIE_BACKEND_BASE_URL",
        "BACKEND_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(api_compat, "_TOKEN", None)


@pytest.fixture
def transport(monkeypatch):
    calls: list[dict] = []

    def fake_request(method, url, **kwargs):
        calls.append({"method": method, "url": url, **kwargs})
        return fake_request.response

    fake_request.response = FakeResponse(200, {})
    fake_request.calls = calls
    monkeypatch.setattr(api_compat.requests, "request", fake_request)
    return fake_request


def test_base_url_defaults_and_environment(monkeypatch):
    assert api_compat.resolve_base_url() == "http://127.0.0.1:8000"
    monkeypatch.setenv("SALES_GENIE_BACKEND_BASE_URL", "http://api.local:9000/")
    assert api_compat.resolve_base_url() == "http://api.local:9000"


def test_lead_is_normalised_for_the_ui():
    lead = api_compat.normalise_lead(
        {
            "id": "7",
            "company_name": "Acme",
            "explicit_needs": "Reduce manual reporting",
            "status": "prospecting",
            "stage": "prospecting",
            "funding_stage": "Series B",
        }
    )
    assert lead["lead_id"] == "7"
    assert lead["business_need"] == "Reduce manual reporting"
    assert lead["lead_status"] == "prospecting"
    assert lead["funding_stage"] == "Series B"


def test_create_payload_maps_ui_fields_and_stage_alias():
    payload = api_compat.lead_payload(
        {
            "company_name": "Acme",
            "business_need": "Scale ETL",
            "lead_status": "Proposal Sent",
        }
    )
    assert payload["explicit_needs"] == "Scale ETL"
    assert payload["stage"] == "proposal"
    assert "lead_status" not in payload


def test_score_keeps_missing_probability_and_labels_dimensions():
    score = api_compat.normalise_score(
        {
            "lead_id": 3,
            "score": 82,
            "priority_level": "hot",
            "conversion_probability": None,
            "explanation": "No calibrated model is configured.",
            "recommended_next_action": "Schedule discovery.",
            "factors": [
                {"name": "Company Fit", "dimension": "Fit"},
                {"name": "Intent", "dimension": "Intent"},
            ],
        }
    )
    assert score["lead_score"] == 82
    assert score["conversion_probability"] is None
    assert score["scoring_factors"] == ["Company Fit (Fit)", "Intent"]
    assert score["next_action"] == "Schedule discovery."


def test_insight_post_shape_is_flat_and_joins_hypotheses():
    # POST /leads/{id}/insights returns a flat LeadIntelligence.
    insight = api_compat.normalise_insight(
        {
            "company_overview": "A logistics operator.",
            "possible_needs": [{"statement": "Automate exceptions", "rationale": "x"}],
            "opportunities": [{"statement": "Reduce handling cost", "rationale": "y"}],
            "product_industry_fit": "Strong fit.",
            "qualification": {"category": "Qualified", "confidence": "medium"},
            "confidence": "medium",
        }
    )
    assert insight["business_needs"] == "Automate exceptions"
    assert insight["opportunities"] == "Reduce handling cost"
    assert insight["industry_situation"] == "A logistics operator."
    assert insight["qualification_category"] == "Qualified"
    assert insight["confidence"] == "medium"


def test_insight_persisted_row_shape_is_supported():
    # GET /leads/{id}/insights returns stored rows with different key names.
    insight = api_compat.normalise_insight(
        {
            "industry_context": "A retail chain.",
            "business_needs": [{"statement": "Unify stock data"}],
            "opportunities": [{"statement": "Cut stockouts"}],
            "recommended_value_proposition": "Good fit.",
            "qualification": {"category": "Nurture"},
        }
    )
    assert insight["business_needs"] == "Unify stock data"
    assert insight["opportunities"] == "Cut stockouts"
    assert insight["industry_situation"] == "A retail chain."
    assert insight["product_industry_fit"] == "Good fit."
    assert insight["qualification_category"] == "Nurture"


def test_insight_with_no_context_says_so():
    insight = api_compat.normalise_insight({})
    assert "No explicit need" in insight["business_needs"]
    assert "No opportunity" in insight["opportunities"]
    assert "No company overview" in insight["industry_situation"]


def test_saved_analysis_list_returns_newest_and_handles_empty(transport):
    transport.response = FakeResponse(
        200,
        [
            {"industry_context": "Newest.", "business_needs": [{"statement": "A"}]},
            {"industry_context": "Older.", "business_needs": [{"statement": "B"}]},
        ],
    )
    ok, data = api_compat.api_get("http://api.local", "/intelligence/analyze/4")
    assert ok is True
    assert data["industry_situation"] == "Newest."

    transport.response = FakeResponse(200, [])
    ok, data = api_compat.api_get("http://api.local", "/intelligence/analyze/4")
    assert ok is False
    assert data["status_code"] == 404
    assert "No saved analysis" in data["error"]


def test_draft_maps_subject_and_body():
    draft = api_compat.normalise_draft(
        {"subject_line": "Quick question", "body": "Hello", "channel": "Email"}
    )
    assert draft["email_subject"] == "Quick question"
    assert draft["email_content"] == "Hello"


def test_analytics_derives_bands_and_industries():
    dashboard = api_compat.normalise_analytics(
        {
            "total_leads": 5,
            "conversion_rate": {"value": 0.2},
            "outreach_activity": 4,
            "interactions_logged": 2,
            "lead_score_distribution": [
                {"band": "70-100", "count": 2},
                {"band": "45-69", "count": 1},
                {"band": "0-44", "count": 1},
            ],
        },
        [{"industry": "Software"}, {"industry": "Software"}, {"industry": ""}],
    )
    assert dashboard["hot_leads"] == 2
    assert dashboard["warm_leads"] == 1
    assert dashboard["cold_leads"] == 1
    assert dashboard["conversion_rate"] == 20.0
    assert dashboard["emails_generated"] == 4
    assert dashboard["emails_sent"] == 0
    assert dashboard["industry_distribution"] == {"Software": 2, "Unknown": 1}


def test_bulk_records_become_importable_csv():
    content = api_compat.records_to_csv(
        [
            {
                "company_name": "Acme",
                "business_need": "Scale ETL",
                "lead_status": "Qualified",
                "email": "a@acme.test",
            }
        ]
    ).decode("utf-8")
    assert "company_name" in content
    assert "business_need" in content
    assert "Scale ETL" in content
    assert "qualified" in content


def test_get_leads_calls_canonical_path_and_normalises(transport):
    transport.response = FakeResponse(200, [{"id": "1", "company_name": "Acme"}])
    ok, data = api_compat.api_get("http://api.local", "/leads/")
    assert ok is True
    assert data[0]["lead_id"] == "1"
    call = transport.calls[0]
    assert call["method"] == "GET"
    assert call["url"] == "http://api.local/api/v1/leads"
    assert call["params"] == {"page_size": 500}


def test_create_lead_wraps_response_for_the_ui(transport):
    transport.response = FakeResponse(201, {"id": "9", "company_name": "Acme"})
    ok, data = api_compat.api_post(
        "http://api.local", "/leads/", json_data={"company_name": "Acme"}
    )
    assert ok is True
    assert data["lead"]["lead_id"] == "9"
    assert data["message"]
    assert transport.calls[0]["url"] == "http://api.local/api/v1/leads"


def test_bulk_import_sends_a_csv_file(transport):
    transport.response = FakeResponse(
        200, {"imported": 2, "duplicates": 1, "invalid": 0}
    )
    ok, data = api_compat.api_post(
        "http://api.local",
        "/leads/bulk",
        json_data=[{"company_name": "Acme"}, {"company_name": "Globex"}],
    )
    assert ok is True
    assert data["message"] == "2 imported, 1 duplicates, 0 invalid."
    call = transport.calls[0]
    assert call["url"] == "http://api.local/api/v1/leads/import"
    assert call["files"]["file"][0] == "leads.csv"


def test_send_email_reports_unconfigured_transport(transport):
    transport.response = FakeResponse(
        501, {"detail": "No e-mail delivery provider is configured."}
    )
    ok, data = api_compat.api_post(
        "http://api.local",
        "/outreach/send-email",
        json_data={"lead_id": "1", "subject": "Hi", "body": "Hello"},
    )
    assert ok is False
    assert data["configured"] is False
    assert data["success"] is False
    assert "e-mail delivery provider" in data["message"]


def test_missing_draft_is_reported_not_faked(transport):
    transport.response = FakeResponse(200, [])
    ok, data = api_compat.api_get("http://api.local", "/intelligence/outreach/4")
    assert ok is False
    assert data["status_code"] == 404


def test_auth_error_is_actionable(transport):
    transport.response = FakeResponse(401, {"detail": "Not authenticated"})
    ok, data = api_compat.api_get("http://api.local", "/leads/")
    assert ok is False
    assert "SALES_GENIE_BACKEND_TOKEN" in data["error"]
