"""Intelligence, outreach, scoring, conversation, analytics and CRM endpoints."""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Module 2 - company analysis / lead intelligence
# ---------------------------------------------------------------------------
def test_insights_generate_persist_and_are_evidence_aware(client, lead, rep):
    response = client.post(f"/api/v1/leads/{lead['id']}/insights", headers=rep)
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["lead_id"] == int(lead["id"])
    assert body["qualification"]["category"] in {
        "Qualified",
        "Nurture",
        "Disqualify",
        "Needs discovery",
    }
    assert body["supported_facts"], "supplied fields must become supported facts"
    assert body["missing_information"], "absent fields must be reported, not invented"
    assert "No website retrieval" in body["company_overview"]
    assert body["execution"]["engine"] == "heuristic"
    assert body["execution"]["used_mock"] is True

    listed = client.get(f"/api/v1/leads/{lead['id']}/insights", headers=rep)
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 1
    assert rows[0]["id"] == body["id"]
    assert rows[0]["provider"] == "heuristic"


def test_insights_unknown_lead_returns_404(client, rep):
    response = client.post("/api/v1/leads/9999/insights", headers=rep)
    assert response.status_code == 404
    assert response.json()["code"] == "lead_not_found"


def test_insights_accept_optional_product_context(client, lead, rep):
    response = client.post(
        f"/api/v1/leads/{lead['id']}/insights",
        headers=rep,
        json={"product_service": "SalesGenie AI", "extra_context": "Met at a conference."},
    )
    assert response.status_code == 200, response.text
    assert "SalesGenie AI" in response.json()["product_industry_fit"]


# ---------------------------------------------------------------------------
# Module 3 - outreach generation
# ---------------------------------------------------------------------------
def test_outreach_generation_persists_a_draft(client, lead, rep):
    response = client.post(
        "/api/v1/outreach/generate",
        headers=rep,
        json={
            "lead_id": int(lead["id"]),
            "tone": "formal",
            "length": "short",
            "outreach_type": "cold_email",
            "goal": "book a discovery call",
            "pain_points": ["manual reporting"],
            "product_service": "SalesGenie AI",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["channel"] == "Email"
    assert body["subject_line"]
    assert "Dana" in body["body"]
    assert body["status"] == "draft"
    assert body["execution"]["engine"] == "heuristic"

    drafts = client.get(f"/api/v1/leads/{lead['id']}/outreach-drafts", headers=rep)
    assert drafts.status_code == 200
    rows = drafts.json()
    assert len(rows) == 1
    assert rows[0]["id"] == body["id"]
    assert rows[0]["status"] == "draft"
    assert rows[0]["pain_points_used"] == ["manual reporting"]


def test_outreach_generation_validates_enumerations(client, lead, rep):
    bad_length = client.post(
        "/api/v1/outreach/generate",
        headers=rep,
        json={"lead_id": int(lead["id"]), "length": "epic"},
    )
    assert bad_length.status_code == 422

    bad_type = client.post(
        "/api/v1/outreach/generate",
        headers=rep,
        json={"lead_id": int(lead["id"]), "outreach_type": "carrier_pigeon"},
    )
    assert bad_type.status_code == 422


def test_outreach_generation_unknown_lead_returns_404(client, rep):
    response = client.post(
        "/api/v1/outreach/generate", headers=rep, json={"lead_id": 9999}
    )
    assert response.status_code == 404


def test_outreach_draft_can_be_edited_and_marked_sent(client, lead, rep):
    generated = client.post(
        "/api/v1/outreach/generate",
        headers=rep,
        json={"lead_id": int(lead["id"])},
    ).json()

    edited = client.patch(
        f"/api/v1/outreach/campaigns/{generated['id']}",
        headers=rep,
        json={
            "subject": "Edited subject",
            "body": "Edited body text.",
            "tone": "friendly",
            "status": "approved",
        },
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["subject"] == "Edited subject"
    assert edited.json()["status"] == "approved"
    assert edited.json()["provider"] == "user-supplied"

    sent = client.post(
        f"/api/v1/outreach/campaigns/{generated['id']}/mark-sent", headers=rep
    )
    assert sent.status_code == 200
    assert sent.json()["status"] == "sent"


def test_outreach_send_never_sends_and_reports_501(client, lead, rep):
    response = client.post(
        "/api/v1/outreach/send", headers=rep, json={"lead_id": int(lead["id"])}
    )
    assert response.status_code == 501
    body = response.json()
    assert body["code"] == "email_transport_not_configured"
    assert "never sends" in body["detail"]


def test_outreach_missing_campaign_returns_404(client, rep):
    assert (
        client.get("/api/v1/outreach/campaigns/424242", headers=rep).status_code == 404
    )


# ---------------------------------------------------------------------------
# Module 4 - scoring
# ---------------------------------------------------------------------------
def test_scoring_is_explainable_and_never_fakes_probability(client, lead, rep):
    response = client.post(f"/api/v1/leads/{lead['id']}/scores", headers=rep)
    assert response.status_code == 200, response.text
    body = response.json()

    assert 0 <= body["score"] <= 100
    assert body["qualification_category"] in {"Qualified", "Nurture", "Low priority"}
    assert len(body["factors"]) == 4
    names = {factor["name"] for factor in body["factors"]}
    assert names == {"Company fit", "Intent", "Engagement", "Decision readiness"}
    assert abs(sum(factor["weight"] for factor in body["factors"]) - 100) < 0.001
    for factor in body["factors"]:
        assert 0 <= factor["normalized_value"] <= 1
        assert factor["explanation"]

    # A heuristic must never be presented as a calibrated probability.
    assert body["conversion_probability"] is None
    assert body["probability_band"] in {"low", "medium", "high"}
    assert "statistical probability" in body["probability_note"]
    assert "Not a trained or calibrated predictive model" in body["methodology_note"]
    assert body["model_version"].startswith("heuristic:")

    latest = client.get(f"/api/v1/leads/{lead['id']}/scores/latest", headers=rep)
    assert latest.status_code == 200
    assert latest.json()["id"] == body["id"]
    assert latest.json()["score"] == body["score"]


def test_latest_score_before_scoring_returns_404(client, lead, rep):
    response = client.get(f"/api/v1/leads/{lead['id']}/scores/latest", headers=rep)
    assert response.status_code == 404
    assert response.json()["code"] == "score_not_found"


def test_scoring_history_is_append_only(client, lead, rep):
    first = client.post(f"/api/v1/leads/{lead['id']}/scores", headers=rep).json()
    second = client.post(f"/api/v1/leads/{lead['id']}/scores", headers=rep).json()
    history = client.get(f"/api/v1/leads/{lead['id']}/scores", headers=rep).json()
    assert len(history) == 2
    assert {row["id"] for row in history} == {first["id"], second["id"]}


def test_scoring_requires_write_role(client, lead, viewer):
    response = client.post(f"/api/v1/leads/{lead['id']}/scores", headers=viewer)
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Module 5 - conversation intelligence
# ---------------------------------------------------------------------------
def test_conversation_summary_persists_interaction(client, lead, rep):
    transcript = (
        "Dana explained that reporting is manual and slow. "
        "Dana will send the current spreadsheet by Friday. "
        "She is interested in an integration demo next month."
    )
    response = client.post(
        "/api/v1/conversations/summarize",
        headers=rep,
        json={
            "lead_id": int(lead["id"]),
            "transcript": transcript,
            "interaction_type": "call",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["executive_summary"]
    assert body["action_items"]
    assert body["execution"]["engine"] == "heuristic"

    listed = client.get(f"/api/v1/leads/{lead['id']}/conversations", headers=rep)
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 1
    assert rows[0]["id"] == body["id"]
    assert rows[0]["interaction_type"] == "call"

    fetched = client.get(f"/api/v1/conversations/{body['id']}", headers=rep)
    assert fetched.status_code == 200
    assert fetched.json()["summary"] == body["executive_summary"]


def test_conversation_requires_content(client, lead, rep):
    response = client.post(
        "/api/v1/conversations/summarize",
        headers=rep,
        json={"lead_id": int(lead["id"]), "transcript": "  ", "notes": ""},
    )
    assert response.status_code == 422


def test_conversation_unknown_lead_returns_404(client, rep):
    response = client.post(
        "/api/v1/conversations/summarize",
        headers=rep,
        json={"lead_id": 9999, "transcript": "Some text that is long enough."},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Module 6 - analytics, follow-ups and recommendations
# ---------------------------------------------------------------------------
def test_analytics_returns_only_defensible_metrics(client, lead, rep):
    client.post(f"/api/v1/leads/{lead['id']}/scores", headers=rep)

    response = client.get("/api/v1/analytics", headers=rep)
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["total_leads"] == 1
    assert body["qualified_leads"] == 1
    assert body["converted_leads"] == 0
    assert body["average_lead_score"] is not None
    assert body["conversion_rate"]["value"] == 0.0
    assert body["conversion_rate"]["pending_definition"] is False

    # Undefined KPIs must be null with an explicit flag, never invented.
    for key in ("pipeline_value", "average_response_time_days", "average_sales_cycle_days"):
        assert body[key]["value"] is None
        assert body[key]["pending_definition"] is True

    assert len(body["pipeline_distribution"]) == 7
    assert len(body["activity_trend"]) == 14
    assert body["source"] == "database"


def test_follow_ups_are_derived_from_stored_scores(client, lead, rep):
    assert client.get("/api/v1/follow-ups", headers=rep).json() == []

    client.post(f"/api/v1/leads/{lead['id']}/scores", headers=rep)
    response = client.get("/api/v1/follow-ups", headers=rep)
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["lead_id"] == lead["id"]
    assert rows[0]["score"] is not None
    assert rows[0]["recommended_action"]


def test_terminal_leads_are_excluded_from_follow_ups(client, lead, rep):
    client.post(f"/api/v1/leads/{lead['id']}/scores", headers=rep)
    client.patch(
        f"/api/v1/leads/{lead['id']}", headers=rep, json={"stage": "converted"}
    )
    assert client.get("/api/v1/follow-ups", headers=rep).json() == []


def test_recommendation_endpoint(client, lead, rep):
    response = client.get(f"/api/v1/recommendations/{lead['id']}", headers=rep)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["priority"] in {"High", "Medium", "Low"}
    assert body["recommended_action"]
    assert body["lead_id"] == lead["id"]
    # FR-032: timing, channel and content strategy must all be present.
    assert body["suggested_channel"] in {"email", "phone", "linkedin", "meeting"}
    assert body["suggested_timing"]
    assert body["follow_up_draft"]


def test_analytics_insights_are_labelled_observations(client, lead, rep):
    response = client.post("/api/v1/analytics/insights", headers=rep)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["insights"]
    assert "do not establish causes or forecast" in body["caveat"]


def test_analytics_snapshot_requires_manager(client, rep, manager):
    assert client.post("/api/v1/analytics/snapshot", headers=rep).status_code == 403
    created = client.post("/api/v1/analytics/snapshot", headers=manager)
    assert created.status_code == 201, created.text
    assert created.json()["id"] >= 1


# ---------------------------------------------------------------------------
# CRM surface (Module 5, planned transport - SRS D-06)
# ---------------------------------------------------------------------------
def test_crm_providers_report_configuration_state(client, rep):
    response = client.get("/api/v1/crm/providers", headers=rep)
    assert response.status_code == 200
    providers = {row["provider"]: row for row in response.json()}
    assert set(providers) == {"salesforce", "hubspot"}
    assert all(row["live_sync_available"] is False for row in providers.values())


def test_crm_mapping_validation(client, rep):
    good = client.post(
        "/api/v1/crm/mappings/validate",
        headers=rep,
        json={"mapping": {"company_name": "Account Name", "email": "Email"}},
    )
    assert good.status_code == 200
    assert good.json()["valid"] is True

    bad = client.post(
        "/api/v1/crm/mappings/validate",
        headers=rep,
        json={"mapping": {"not_a_field": "x"}},
    )
    assert bad.status_code == 200
    assert bad.json()["valid"] is False
    assert bad.json()["errors"]


def test_crm_sync_preview_is_dry_run(client, lead, rep):
    response = client.post(
        "/api/v1/crm/sync/preview",
        headers=rep,
        json={"provider": "salesforce", "lead_ids": [int(lead["id"]), 9999, "abc"]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["dry_run"] is True
    records = {str(row["lead_id"]): row for row in body["records"]}
    assert records[lead["id"]]["valid"] is True
    assert records["9999"]["valid"] is False
    assert records["abc"]["valid"] is False


def test_crm_sync_records_failure_and_retry(client, lead, rep):
    response = client.post(
        "/api/v1/crm/sync",
        headers=rep,
        json={"provider": "hubspot", "lead_ids": [int(lead["id"])]},
    )
    assert response.status_code == 501
    body = response.json()
    assert body["code"] == "crm_not_configured"
    log_id = body["meta"]["sync_log_id"]

    logs = client.get("/api/v1/crm/sync-logs", headers=rep).json()
    assert logs[0]["id"] == log_id
    assert logs[0]["status"] == "failed"
    assert logs[0]["attempt_count"] == 1

    retried = client.post(f"/api/v1/crm/sync-logs/{log_id}/retry", headers=rep)
    assert retried.status_code == 200
    assert retried.json()["attempt_count"] == 2


def test_crm_sync_rejects_unknown_provider(client, rep):
    response = client.post(
        "/api/v1/crm/sync", headers=rep, json={"provider": "pipedrive"}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_provider"


# ---------------------------------------------------------------------------
# System surface
# ---------------------------------------------------------------------------
def test_health_reports_database_and_ai_state(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["auth_enabled"] is True
    assert body["ai_backend"] == "heuristic"
    assert body["ai_status"] == "ok"


def test_openapi_spec_is_served(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    for expected in (
        "/api/v1/leads",
        "/api/v1/leads/{lead_id}",
        "/api/v1/leads/{lead_id}/scores",
        "/api/v1/outreach/generate",
        "/api/v1/analytics",
        "/api/v1/follow-ups",
    ):
        assert expected in paths
