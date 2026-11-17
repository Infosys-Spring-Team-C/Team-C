"""API tests for lead management and CSV ingestion."""

import os

# The application constructs its default engine during import. Keep that unused
# engine isolated from any developer or production database configuration.
os.environ["DATABASE_URL"] = "sqlite://"

import csv
import io
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from database.models import Base, Lead
from main import app


@pytest.fixture
def db_session_factory() -> Generator[sessionmaker[Session], None, None]:
    """Provide a fresh in-memory SQLite database for each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_session_factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    try:
        yield test_session_factory
    finally:
        engine.dispose()


@pytest.fixture
def client(
    db_session_factory: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    """Provide a client whose database dependency uses the test database."""

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


def _lead_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "company_name": "Acme Corp",
        "industry": "Technology",
        "contact_name": "Jordan Lee",
        "lead_status": "new",
        "tech_stack": "Python, PostgreSQL",
        "funding_stage": "Series A",
    }
    payload.update(overrides)
    return payload


def test_create_lead_success(
    client: TestClient, db_session_factory: sessionmaker[Session]
) -> None:
    """Creating a valid lead returns 201 and persists all supplied fields."""
    response = client.post("/leads/", json=_lead_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["lead_id"] > 0
    assert body["company_name"] == "Acme Corp"
    assert body["lead_status"] == "new"
    assert body["created_at"]
    assert body["updated_at"]

    with db_session_factory() as db:
        saved_lead = db.get(Lead, body["lead_id"])
        assert saved_lead is not None
        assert saved_lead.contact_name == "Jordan Lee"


def test_create_lead_missing_fields(client: TestClient) -> None:
    """Missing required lead fields are rejected by request validation."""
    response = client.post(
        "/leads/",
        json={"company_name": "Acme Corp", "industry": "Technology"},
    )

    assert response.status_code == 422
    assert "detail" in response.json()


def test_get_lead_by_id(client: TestClient, db_session_factory: sessionmaker[Session]) -> None:
    """A saved lead can be retrieved with its attributes intact."""
    with db_session_factory() as db:
        lead = Lead(**_lead_payload())
        db.add(lead)
        db.commit()
        db.refresh(lead)
        lead_id = lead.lead_id

    response = client.get(f"/leads/{lead_id}")

    assert response.status_code == 200
    assert response.json()["lead_id"] == lead_id
    assert response.json()["company_name"] == "Acme Corp"
    assert response.json()["contact_name"] == "Jordan Lee"


def test_get_lead_not_found(client: TestClient) -> None:
    """Unknown IDs return 404."""
    response = client.get("/leads/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Lead not found"


def test_list_leads_pagination_and_filters(
    client: TestClient, db_session_factory: sessionmaker[Session]
) -> None:
    """Listing supports page controls and the status and industry filters."""
    with db_session_factory() as db:
        db.add_all(
            [
                Lead(**_lead_payload(company_name="Acme", industry="Technology")),
                Lead(**_lead_payload(company_name="Northwind", industry="Retail")),
                Lead(
                    **_lead_payload(
                        company_name="Contoso", industry="Retail", lead_status="qualified"
                    )
                ),
            ]
        )
        db.commit()

    page = client.get("/leads/?skip=1&limit=1")
    filtered = client.get("/leads/?industry=Retail&lead_status=qualified")

    assert page.status_code == 200
    assert len(page.json()) == 1
    assert page.json()[0]["company_name"] == "Northwind"
    assert filtered.status_code == 200
    assert [lead["company_name"] for lead in filtered.json()] == ["Contoso"]


def test_update_lead(client: TestClient, db_session_factory: sessionmaker[Session]) -> None:
    """A valid lifecycle stage update is persisted and returned."""
    with db_session_factory() as db:
        lead = Lead(**_lead_payload())
        db.add(lead)
        db.commit()
        db.refresh(lead)
        lead_id = lead.lead_id

    response = client.put(f"/leads/{lead_id}", json={"lead_status": "contacted"})

    assert response.status_code == 200
    assert response.json()["lead_status"] == "contacted"
    with db_session_factory() as db:
        saved_lead = db.get(Lead, lead_id)
        assert saved_lead is not None
        assert saved_lead.lead_status == "contacted"


def test_delete_lead(client: TestClient, db_session_factory: sessionmaker[Session]) -> None:
    """Deleting a lead returns 204 and subsequent reads return 404."""
    with db_session_factory() as db:
        lead = Lead(**_lead_payload())
        db.add(lead)
        db.commit()
        lead_id = lead.lead_id

    deleted = client.delete(f"/leads/{lead_id}")
    missing = client.get(f"/leads/{lead_id}")

    assert deleted.status_code == 204
    assert deleted.content == b""
    assert missing.status_code == 404


def test_csv_upload_and_deduplication(
    client: TestClient, db_session_factory: sessionmaker[Session]
) -> None:
    """CSV ingestion inserts new rows and skips case-insensitive duplicates."""
    with db_session_factory() as db:
        db.add(Lead(**_lead_payload()))
        db.commit()

    csv_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        csv_buffer,
        fieldnames=["company_name", "industry", "contact_name", "lead_status"],
    )
    writer.writeheader()
    writer.writerows(
        [
            {
                "company_name": "Acme Corp",
                "industry": "Technology",
                "contact_name": "jordan lee",
                "lead_status": "qualified",
            },
            {
                "company_name": "Northwind",
                "industry": "Retail",
                "contact_name": "Sam Rivera",
                "lead_status": "new",
            },
            {
                "company_name": "Contoso",
                "industry": "Finance",
                "contact_name": "Taylor Morgan",
                "lead_status": "contacted",
            },
        ]
    )

    response = client.post(
        "/leads/upload-csv",
        files={"file": ("leads.csv", csv_buffer.getvalue().encode("utf-8"), "text/csv")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "total_rows": 3,
        "inserted": 2,
        "duplicates_skipped": 1,
        "errors": [],
    }
    with db_session_factory() as db:
        lead_count = db.scalar(select(func.count()).select_from(Lead))
        assert lead_count == 3
        assert db.scalar(select(func.count()).select_from(Lead).where(Lead.company_name == "Northwind")) == 1


def test_csv_upload_empty_file(client: TestClient) -> None:
    """An empty upload returns a zero-count summary."""
    response = client.post(
        "/leads/upload-csv",
        files={"file": ("empty.csv", b"", "text/csv")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "total_rows": 0,
        "inserted": 0,
        "duplicates_skipped": 0,
        "errors": [],
    }


def test_csv_upload_missing_required_headers(client: TestClient) -> None:
    """A CSV without required headers reports the missing columns."""
    response = client.post(
        "/leads/upload-csv",
        files={"file": ("invalid.csv", b"company_name,industry\nAcme,Technology\n", "text/csv")},
    )

    assert response.status_code == 200
    assert response.json()["inserted"] == 0
    assert response.json()["errors"] == [
        {"row": 1, "error": "Missing required columns: contact_name."}
    ]


def test_csv_upload_windows_1252_encoding(client: TestClient) -> None:
    """Windows-1252 CSV content is decoded and imported."""
    response = client.post(
        "/leads/upload-csv",
        files={
            "file": (
                "encoded.csv",
                "company_name,industry,contact_name\nCafé,Food,Renée\n".encode("cp1252"),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["inserted"] == 1
    assert response.json()["errors"] == []
