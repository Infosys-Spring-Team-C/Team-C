"""Integration tests for CRM mapping, synchronization, audit, and RBAC."""

import os
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from typing import Any

os.environ.setdefault("DATABASE_URL", "sqlite://")

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_current_user
from app.database import get_db
from app.services import crm_service
from database.models import Base, CRMSyncLog, Lead
from main import app

TEST_SECRET = "crm-integration-test-secret-key-32-bytes-minimum"


@pytest.fixture
def db_session_factory() -> Generator[sessionmaker[Session], None, None]:
    """Create an isolated in-memory database for CRM integration tests."""
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
    db_session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    """Override database access and set a test-only JWT secret."""
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)

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


def _token(role: str) -> str:
    """Issue a short-lived test JWT for the requested role."""
    return jwt.encode(
        {
            "sub": f"test-{role}",
            "role": role,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        TEST_SECRET,
        algorithm="HS256",
    )


def _auth(role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(role)}"}


def _create_lead(db_session_factory: sessionmaker[Session]) -> int:
    """Persist a lead fixture and return its primary key."""
    with db_session_factory() as db:
        lead = Lead(
            company_name="Northstar Systems",
            industry="Technology",
            contact_name="Morgan Chen",
            lead_status="qualified",
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)
        return lead.lead_id


def test_crm_sync_requires_valid_bearer_token(client: TestClient) -> None:
    response = client.post(
        "/crm/sync/1",
        json={"crm_provider": "salesforce", "action": "sync_contact"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_crm_sync_rejects_user_without_allowed_role(
    client: TestClient, db_session_factory: sessionmaker[Session]
) -> None:
    lead_id = _create_lead(db_session_factory)
    response = client.post(
        f"/crm/sync/{lead_id}",
        headers=_auth("sales_rep"),
        json={"crm_provider": "hubspot", "action": "sync_contact"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient role for this operation."


def test_manager_sync_maps_and_persists_crm_payload(
    client: TestClient, db_session_factory: sessionmaker[Session]
) -> None:
    lead_id = _create_lead(db_session_factory)
    response = client.post(
        f"/crm/sync/{lead_id}",
        headers=_auth("manager"),
        json={"crm_provider": "salesforce", "action": "update_stage"},
    )

    assert response.status_code == 201
    result = response.json()
    assert result["lead_id"] == lead_id
    assert result["crm_provider"] == "salesforce"
    assert result["sync_type"] == "deal_update"
    assert result["status"] == "success"
    assert result["payload"] == {
        "record_type": "deal",
        "company_name": "Northstar Systems",
        "contact_name": "Morgan Chen",
        "stage": "qualified",
    }

    with db_session_factory() as db:
        saved = db.get(CRMSyncLog, result["log_id"])
        assert saved is not None
        assert saved.payload == result["payload"]
        assert saved.error_message is None


def test_admin_sync_failure_is_audited_and_reported_in_status(
    client: TestClient,
    db_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lead_id = _create_lead(db_session_factory)

    def fail_sync(provider: str, payload: dict[str, object]) -> dict[str, Any]:
        raise RuntimeError("CRM provider unavailable")

    monkeypatch.setattr(crm_service, "simulate_crm_sync", fail_sync)
    response = client.post(
        f"/crm/sync/{lead_id}",
        headers=_auth("admin"),
        json={"crm_provider": "hubspot", "action": "activity_log"},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "failed"
    assert response.json()["error_message"] == "CRM provider unavailable"

    status_response = client.get("/crm/status")
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["recent_syncs"] == 1
    assert status_body["recent_failures"] == 1
    assert status_body["failure_rate"] == 1.0


def test_crm_log_history_returns_saved_syncs(
    client: TestClient, db_session_factory: sessionmaker[Session]
) -> None:
    lead_id = _create_lead(db_session_factory)
    for action in ("sync_contact", "activity_log"):
        response = client.post(
            f"/crm/sync/{lead_id}",
            headers=_auth("admin"),
            json={"crm_provider": "salesforce", "action": action},
        )
        assert response.status_code == 201

    history = client.get(f"/crm/logs/{lead_id}")

    assert history.status_code == 200
    assert len(history.json()) == 2
    assert all(entry["lead_id"] == lead_id for entry in history.json())
    with db_session_factory() as db:
        saved = db.scalars(select(CRMSyncLog).where(CRMSyncLog.lead_id == lead_id)).all()
        assert len(saved) == 2


def test_sync_unknown_lead_returns_404_to_authorized_user(client: TestClient) -> None:
    response = client.post(
        "/crm/sync/9999",
        headers=_auth("admin"),
        json={"crm_provider": "salesforce", "action": "sync_contact"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Lead not found"


def test_sync_rejects_unknown_provider(client: TestClient) -> None:
    response = client.post(
        "/crm/sync/1",
        headers=_auth("manager"),
        json={"crm_provider": "dynamics", "action": "sync_contact"},
    )

    assert response.status_code == 422
