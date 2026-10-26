"""Shared pytest fixtures.

Environment variables are configured *before* importing the application so the
engine, settings and JWT secret are deterministic for the whole run.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

_TEST_DIR = Path(tempfile.mkdtemp(prefix="salesgenie-tests-"))
os.environ["JWT_SECRET"] = "unit-test-secret-value-0123456789"
os.environ["AUTH_ENABLED"] = "true"
os.environ["DATABASE_URL"] = f"sqlite:///{(_TEST_DIR / 'test.db').as_posix()}"
os.environ["SALES_GENIE_AI_BACKEND"] = "heuristic"
os.environ["SALES_GENIE_LLM_PROVIDER"] = "mock"
os.environ["SALES_GENIE_ENV"] = "test"

from fastapi.testclient import TestClient  # noqa: E402

from backend.api import app  # noqa: E402
from backend.db import Base, SessionLocal, User, engine  # noqa: E402
from backend.security import hash_password  # noqa: E402

PASSWORDS = {
    "admin@test.local": "admin-password",
    "manager@test.local": "manager-password",
    "rep@test.local": "rep-password",
    "viewer@test.local": "viewer-password",
}


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def seeded_users(db):
    rows = {}
    for email, password in PASSWORDS.items():
        role = email.split("@")[0]
        user = User(
            email=email,
            full_name=role.title(),
            role=role,
            password_hash=hash_password(password),
            is_active=True,
        )
        db.add(user)
        rows[role] = user
    db.commit()
    return rows


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def tokens(client, seeded_users) -> dict[str, str]:
    headers: dict[str, str] = {}
    for email, password in PASSWORDS.items():
        response = client.post(
            "/api/v1/auth/token", data={"username": email, "password": password}
        )
        assert response.status_code == 200, response.text
        headers[email.split("@")[0]] = {
            "Authorization": f"Bearer {response.json()['access_token']}"
        }
    return headers


@pytest.fixture()
def rep(tokens) -> dict[str, str]:
    return tokens["rep"]


@pytest.fixture()
def manager(tokens) -> dict[str, str]:
    return tokens["manager"]


@pytest.fixture()
def admin(tokens) -> dict[str, str]:
    return tokens["admin"]


@pytest.fixture()
def viewer(tokens) -> dict[str, str]:
    return tokens["viewer"]


@pytest.fixture()
def lead(client, rep) -> dict:
    response = client.post(
        "/api/v1/leads",
        headers=rep,
        json={
            "company_name": "Acme Systems",
            "industry": "Software",
            "contact_name": "Dana Scully",
            "email": "dana@acme.test",
            "company_size": "51-200",
            "company_description": "A growing B2B software company modernising reporting.",
            "prospect_role": "VP Sales",
            "explicit_needs": "Reduce manual reporting effort across the sales team.",
            "engagement_history": "Meeting booked for discovery",
            "stage": "qualified",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()
