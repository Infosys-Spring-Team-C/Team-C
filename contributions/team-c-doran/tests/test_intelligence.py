"""Integration tests for health, outreach, and lead scoring endpoints."""

import os

os.environ["DATABASE_URL"] = "sqlite://"

from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.services import ai_service
from database.models import Base, Lead, LeadScore, OutreachCampaign
from main import app


@pytest.fixture
def db_session_factory() -> Generator[sessionmaker[Session], None, None]:
    """Provide a fresh SQLite database for each intelligence test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        engine.dispose()


@pytest.fixture
def client(
    db_session_factory: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    """Override the API database dependency with the test database."""

    def override_get_db() -> Generator[Session, None, None]:
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


def _create_lead(db_session_factory: sessionmaker[Session], **overrides: Any) -> int:
    """Persist a lead fixture and return its ID."""
    values: dict[str, Any] = {
        "company_name": "Acme Corp",
        "industry": "Technology",
        "contact_name": "Jordan Lee",
        "lead_status": "qualified",
        "funding_stage": "Series A",
        "tech_stack": "Python, PostgreSQL",
        "company_size": "51-200",
        "revenue": 2_500_000,
    }
    values.update(overrides)
    with db_session_factory() as db:
        lead = Lead(**values)
        db.add(lead)
        db.commit()
        db.refresh(lead)
        return lead.lead_id


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "SalesGenie API"}


def test_outreach_generation_and_history(
    client: TestClient, db_session_factory: sessionmaker[Session]
) -> None:
    lead_id = _create_lead(db_session_factory)

    generated = client.post(
        "/intelligence/outreach",
        json={
            "lead_id": lead_id,
            "tone": "friendly",
            "focus_points": "improving sales team productivity",
        },
    )

    assert generated.status_code == 201
    campaign = generated.json()
    assert campaign["lead_id"] == lead_id
    assert campaign["campaign_id"] > 0
    assert campaign["email_subject"]
    assert "Jordan Lee" in campaign["email_content"]
    assert "improving sales team productivity" in campaign["email_content"]
    assert campaign["follow_up_strategy"]

    history = client.get(f"/intelligence/outreach/{lead_id}")
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["campaign_id"] == campaign["campaign_id"]

    with db_session_factory() as db:
        saved = db.get(OutreachCampaign, campaign["campaign_id"])
        assert saved is not None
        assert saved.tone == "friendly"


def test_outreach_missing_lead_returns_404(client: TestClient) -> None:
    response = client.post("/intelligence/outreach", json={"lead_id": 9999})

    assert response.status_code == 404
    assert response.json()["detail"] == "Lead not found"


def test_scoring_upsert_and_read(
    client: TestClient, db_session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    lead_id = _create_lead(db_session_factory)

    scored = client.post(f"/intelligence/score/{lead_id}")

    assert scored.status_code == 200
    first_score = scored.json()
    assert first_score["lead_id"] == lead_id
    assert first_score["lead_score"] == 100
    assert first_score["conversion_probability"] == 1.0
    assert first_score["priority_level"] == "high"
    assert isinstance(first_score["scoring_factors"], dict)
    assert first_score["score_id"] > 0

    monkeypatch.setattr(
        ai_service,
        "score_lead",
        lambda lead: {
            "lead_score": 45,
            "conversion_probability": 0.45,
            "priority_level": "medium",
            "scoring_factors": {"test_override": {"points": 45}},
        },
    )
    updated = client.post(f"/intelligence/score/{lead_id}")
    assert updated.status_code == 200
    second_score = updated.json()
    assert second_score["score_id"] == first_score["score_id"]
    assert second_score["lead_score"] == 45
    assert second_score["priority_level"] == "medium"

    current = client.get(f"/intelligence/score/{lead_id}")
    assert current.status_code == 200
    assert current.json() == second_score
    with db_session_factory() as db:
        rows = db.scalars(select(LeadScore).where(LeadScore.lead_id == lead_id)).all()
        assert len(rows) == 1


def test_scoring_missing_lead_returns_404(client: TestClient) -> None:
    response = client.post("/intelligence/score/9999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Lead not found"


def test_scoring_invalid_service_output_returns_502(
    client: TestClient,
    db_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lead_id = _create_lead(db_session_factory)
    monkeypatch.setattr(ai_service, "score_lead", lambda lead: '{"lead_score": 100}')

    response = client.post(f"/intelligence/score/{lead_id}")

    assert response.status_code == 502
    assert response.json()["detail"] == "Scoring service returned an invalid response."


def test_get_score_before_calculation_returns_404(
    client: TestClient, db_session_factory: sessionmaker[Session]
) -> None:
    lead_id = _create_lead(db_session_factory)

    response = client.get(f"/intelligence/score/{lead_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Lead score not found"
