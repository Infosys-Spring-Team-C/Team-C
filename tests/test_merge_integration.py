"""Tests for the merged AI, CRM and demo-seed integration.

These cover the parts added while combining the AI package (team-c-mahi), the
backend (team-c-doran) and the database workspace (team_c_sai): automatic
engine/provider selection, AI-factor aggregation into the four SRS dimensions,
the CRM simulator, health metadata and the richer demo seed.
"""
from __future__ import annotations

from types import SimpleNamespace

from backend.config import Settings
from backend.db import Lead, SessionLocal
from backend.intelligence import reset_engine_cache
from backend.routers.scoring import dimension_scores


def test_auto_engine_uses_the_ai_package_with_mock_when_no_key(monkeypatch):
    import backend.intelligence as intelligence

    monkeypatch.setattr(
        intelligence,
        "get_settings",
        lambda: Settings(ai_backend="auto", ai_provider="auto", jwt_secret="x" * 40),
    )
    monkeypatch.setattr(intelligence, "external_package_available", lambda: True)
    reset_engine_cache()
    try:
        engine = intelligence.get_engine()
        assert engine.name == "external"
        assert engine.provider == "mock"
        assert engine.used_mock is True
    finally:
        reset_engine_cache()


def test_auto_engine_falls_back_to_heuristic_when_package_is_missing(monkeypatch):
    import backend.intelligence as intelligence

    monkeypatch.setattr(
        intelligence,
        "get_settings",
        lambda: Settings(ai_backend="auto", ai_provider="auto", jwt_secret="x" * 40),
    )
    monkeypatch.setattr(intelligence, "external_package_available", lambda: False)
    reset_engine_cache()
    try:
        engine = intelligence.get_engine()
        assert engine.name == "heuristic"
    finally:
        reset_engine_cache()


def test_ai_eight_factor_model_maps_onto_four_srs_dimensions():
    factors = [
        SimpleNamespace(name="Company Fit", dimension="Fit", points=80.0, weight=100.0),
        SimpleNamespace(name="Industry Relevance", dimension="Fit", points=60.0, weight=100.0),
        SimpleNamespace(name="Company Size", dimension="Fit", points=40.0, weight=100.0),
        SimpleNamespace(name="Explicit Needs", dimension="Intent", points=90.0, weight=100.0),
        SimpleNamespace(name="Response Behavior", dimension="Intent", points=50.0, weight=100.0),
        SimpleNamespace(name="Engagement History", dimension="Engagement", points=70.0, weight=100.0),
        SimpleNamespace(
            name="Contact Role", dimension="Decision readiness", points=30.0, weight=100.0
        ),
        SimpleNamespace(
            name="Sales Stage", dimension="Decision readiness", points=10.0, weight=100.0
        ),
    ]

    result = dimension_scores(factors)

    assert result == {
        "fit_score": 60,
        "intent_score": 70,
        "engagement_score": 70,
        "decision_readiness_score": 20,
    }


def test_heuristic_four_factor_scores_are_kept_verbatim():
    factors = [
        SimpleNamespace(name="Company fit", dimension=None, points=75.0, weight=100.0),
        SimpleNamespace(name="Intent", dimension=None, points=50.0, weight=100.0),
        SimpleNamespace(name="Engagement", dimension=None, points=25.0, weight=100.0),
        SimpleNamespace(name="Decision readiness", dimension=None, points=100.0, weight=100.0),
    ]

    result = dimension_scores(factors)

    assert result == {
        "fit_score": 75,
        "intent_score": 50,
        "engagement_score": 25,
        "decision_readiness_score": 100,
    }


def test_crm_simulation_is_labelled_and_audited(client, lead, rep):
    response = client.post(
        "/api/v1/crm/sync",
        headers=rep,
        json={
            "provider": "salesforce",
            "operation": "update_stage",
            "lead_ids": [int(lead["id"])],
            "simulate": True,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mode"] == "simulated"
    assert body["simulated"] is True
    assert "No Salesforce or HubSpot request was made" in body["note"]
    record = body["records"][0]
    assert record["status"] == "success"
    assert record["payload"]["record_type"] == "deal"
    assert record["payload"]["stage"] == lead["stage"]

    status = client.get("/api/v1/crm/status", headers=rep)
    assert status.status_code == 200, status.text
    state = status.json()
    assert state["connectivity"] == "simulated"
    assert state["live_transport_available"] is False
    assert state["recent_syncs"] >= 1


def test_crm_simulation_requires_a_lead_id(client, rep):
    response = client.post(
        "/api/v1/crm/sync",
        headers=rep,
        json={"provider": "hubspot", "simulate": True},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_lead_ids"


def test_health_exposes_non_secret_ai_metadata(client):
    body = client.get("/api/v1/health").json()
    for key in ("ai_provider", "ai_model", "ai_used_mock", "ai_mode", "ai_status"):
        assert key in body
    assert body["ai_mode"] in {"live-model", "offline-mock", "unavailable"}


def test_seed_demo_creates_rich_idempotent_records():
    from backend.cli import seed_demo

    seed_demo(confirm=True)
    with SessionLocal() as db:
        first = db.query(Lead).count()
        assert first >= 6
        northwind = db.query(Lead).filter(Lead.email_key == "ada@northwind.example").one()
        assert northwind.pain_points
        assert northwind.explicit_needs
        assert northwind.engagement_history
        assert northwind.company_description

    seed_demo(confirm=True)
    with SessionLocal() as db:
        assert db.query(Lead).count() == first
