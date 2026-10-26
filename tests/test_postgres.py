"""Real PostgreSQL integration tests.

Skipped unless ``TEST_DATABASE_URL`` points at a database whose name contains
``test``.  The fixture drops and recreates the ``public`` schema, so it refuses
to run against anything that does not look like a throw-away test database.

Example::

    $env:TEST_DATABASE_URL = "postgresql+psycopg://postgres@127.0.0.1:55432/salesgenie_test"
    python -m pytest tests/test_postgres.py -q
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from backend.config import reset_settings_cache
from backend.db import (
    CompanyInsight,
    CRMSyncLog,
    Lead,
    LeadScore,
    OutreachCampaign,
    SalesInteraction,
)

ROOT = Path(__file__).resolve().parents[1]
PG_URL = os.getenv("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not PG_URL, reason="TEST_DATABASE_URL is not set; PostgreSQL tests skipped"
)

EXPECTED_TABLES = {
    "users",
    "leads",
    "company_insights",
    "outreach_campaigns",
    "lead_scores",
    "sales_interactions",
    "crm_sync_logs",
    "sales_analytics",
}


def _assert_safe_database(url: str) -> None:
    database = url.rsplit("/", 1)[-1].split("?", 1)[0].lower()
    if "test" not in database:
        pytest.skip(f"refusing to run destructive tests against database {database!r}")


@pytest.fixture(scope="module")
def pg_engine():
    _assert_safe_database(PG_URL)
    engine = create_engine(PG_URL, pool_pre_ping=True, future=True)

    with engine.connect() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        connection.commit()

    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = PG_URL
    reset_settings_cache()
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    try:
        command.upgrade(config, "head")
        yield engine
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        reset_settings_cache()
        engine.dispose()


@pytest.fixture()
def session(pg_engine):
    factory = sessionmaker(bind=pg_engine, autoflush=False, expire_on_commit=False)
    db = factory()
    try:
        yield db
        db.rollback()
    finally:
        db.close()


def test_migration_created_all_tables(pg_engine):
    names = set(inspect(pg_engine).get_table_names())
    assert names == EXPECTED_TABLES | {"alembic_version"}

    with pg_engine.connect() as connection:
        version = connection.execute(text("select version_num from alembic_version")).scalar()
    assert version == "0001_canonical_schema"


def test_foreign_keys_use_cascade_and_set_null(pg_engine):
    inspector = inspect(pg_engine)

    insight_fks = inspector.get_foreign_keys("company_insights")
    assert any(
        fk["referred_table"] == "leads" and fk["options"].get("ondelete") == "CASCADE"
        for fk in insight_fks
    )

    lead_fks = inspector.get_foreign_keys("leads")
    assert any(
        fk["referred_table"] == "users" and fk["options"].get("ondelete") == "SET NULL"
        for fk in lead_fks
    )

    log_fks = inspector.get_foreign_keys("crm_sync_logs")
    assert any(
        fk["referred_table"] == "leads" and fk["options"].get("ondelete") == "SET NULL"
        for fk in log_fks
    )


def test_indexes_exist_on_postgres(pg_engine):
    with pg_engine.connect() as connection:
        indexes = {
            row[0]
            for row in connection.execute(
                text("select indexname from pg_indexes where schemaname = 'public'")
            )
        }
    assert {
        "ix_leads_email_key",
        "ix_leads_stage_created",
        "ix_leads_company_contact",
        "ix_lead_scores_lead_created",
        "ix_lead_scores_score_prob",
        "ix_outreach_lead_status",
        "ix_sales_interactions_lead_date",
        "ix_crm_sync_provider_status",
    } <= indexes


def test_orm_round_trip_and_cascade_on_postgres(session):
    lead = Lead(
        company_name="Postgres Co",
        email="pg@test.local",
        email_key="pg@test.local",
        lifecycle_stage="qualified",
    )
    session.add(lead)
    session.commit()

    session.add(CompanyInsight(lead_id=lead.id, industry_context="pg"))
    session.add(
        OutreachCampaign(lead_id=lead.id, subject="Hi", body="Body", status="draft")
    )
    session.add(
        LeadScore(
            lead_id=lead.id,
            score=80,
            priority_level="hot",
            factors=[{"name": "Company fit", "weight": 30}],
            explanation="pg",
            recommended_next_action="call",
        )
    )
    session.add(
        SalesInteraction(lead_id=lead.id, transcript="t", summary="s")
    )
    session.add(
        CRMSyncLog(lead_id=lead.id, provider="salesforce", status="failed")
    )
    session.commit()

    assert session.query(LeadScore).filter_by(lead_id=lead.id).one().factors[0]["weight"] == 30

    session.delete(lead)
    session.commit()

    assert session.query(CompanyInsight).count() == 0
    assert session.query(OutreachCampaign).count() == 0
    assert session.query(LeadScore).count() == 0
    assert session.query(SalesInteraction).count() == 0
    # SET NULL: the log survives without the lead.
    log = session.query(CRMSyncLog).one()
    assert log.lead_id is None


def test_unique_email_key_is_enforced_on_postgres(session):
    session.add(Lead(company_name="A", email="dup@pg.test", email_key="dup@pg.test"))
    session.commit()
    session.add(Lead(company_name="B", email="dup@pg.test", email_key="dup@pg.test"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_jsonb_columns_accept_structured_values(session):
    lead = Lead(company_name="JSON PG Co")
    session.add(lead)
    session.commit()
    session.add(
        CompanyInsight(
            lead_id=lead.id,
            business_needs=[{"statement": "Need better reporting", "confidence": "low"}],
            qualification={"category": "Nurture"},
        )
    )
    session.commit()

    row = session.query(CompanyInsight).filter_by(lead_id=lead.id).one()
    assert row.business_needs[0]["statement"] == "Need better reporting"
    assert row.qualification["category"] == "Nurture"
