"""Schema, migration and referential-integrity tests.

These run against SQLite (fast, in-process).  The equivalent PostgreSQL checks
live in ``test_postgres.py`` and are gated on ``TEST_DATABASE_URL``.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError

from backend.config import reset_settings_cache
from backend.db import Base, CompanyInsight, Lead, LeadScore

ROOT = Path(__file__).resolve().parents[1]

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


def _alembic_config() -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    return config


def test_models_declare_the_canonical_eight_tables():
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_leads_have_lifecycle_and_owner_columns():
    columns = Base.metadata.tables["leads"].columns
    assert "lifecycle_stage" in columns
    assert columns["lifecycle_stage"].nullable is False
    assert "owner_id" in columns
    assert "email_key" in columns


def test_migration_creates_and_drops_the_schema(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    reset_settings_cache()
    config = _alembic_config()
    try:
        command.upgrade(config, "head")

        engine = create_engine(url)
        inspector = inspect(engine)
        assert set(inspector.get_table_names()) == EXPECTED_TABLES | {"alembic_version"}

        lead_indexes = {index["name"]: index for index in inspector.get_indexes("leads")}
        assert bool(lead_indexes["ix_leads_email_key"]["unique"]) is True
        assert "ix_leads_stage_created" in lead_indexes
        assert "ix_leads_company_contact" in lead_indexes

        score_indexes = {
            index["name"] for index in inspector.get_indexes("lead_scores")
        }
        assert {"ix_lead_scores_lead_created", "ix_lead_scores_score_prob"} <= score_indexes

        insight_fks = inspector.get_foreign_keys("company_insights")
        assert any(fk["referred_table"] == "leads" for fk in insight_fks)

        command.downgrade(config, "base")
        remaining = set(inspect(create_engine(url)).get_table_names())
        assert remaining <= {"alembic_version"}
    finally:
        reset_settings_cache()


def test_migration_matches_orm_metadata(tmp_path, monkeypatch):
    """Every ORM table/column must exist after ``alembic upgrade head``."""
    url = f"sqlite:///{(tmp_path / 'parity.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    reset_settings_cache()
    try:
        command.upgrade(_alembic_config(), "head")
        inspector = inspect(create_engine(url))
        for table in EXPECTED_TABLES:
            migrated = {column["name"] for column in inspector.get_columns(table)}
            orm = set(Base.metadata.tables[table].columns.keys())
            assert orm <= migrated, f"{table} is missing columns: {orm - migrated}"
    finally:
        reset_settings_cache()


def test_cascade_delete_removes_dependent_rows(db):
    lead = Lead(company_name="Cascade Co", email="cascade@test.local", email_key="cascade@test.local")
    db.add(lead)
    db.commit()

    db.add(CompanyInsight(lead_id=lead.id, industry_context="ctx"))
    db.add(
        LeadScore(
            lead_id=lead.id,
            score=50,
            priority_level="warm",
            factors=[],
            explanation="test",
            recommended_next_action="follow up",
        )
    )
    db.commit()
    assert db.query(CompanyInsight).count() == 1
    assert db.query(LeadScore).count() == 1

    db.delete(lead)
    db.commit()
    assert db.query(CompanyInsight).count() == 0
    assert db.query(LeadScore).count() == 0


def test_email_key_uniqueness_is_enforced(db):
    db.add(Lead(company_name="A", email="dup@test.local", email_key="dup@test.local"))
    db.commit()
    db.add(Lead(company_name="B", email="dup@test.local", email_key="dup@test.local"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_leads_without_email_do_not_collide(db):
    db.add(Lead(company_name="No Email A", email="", email_key=None))
    db.add(Lead(company_name="No Email B", email="", email_key=None))
    db.commit()
    assert db.query(Lead).count() == 2


def test_json_columns_round_trip(db):
    lead = Lead(company_name="JSON Co")
    db.add(lead)
    db.commit()

    factors = [
        {
            "name": "Company fit",
            "weight": 30,
            "normalized_value": 1.0,
            "points": 30.0,
            "explanation": "all signals present",
            "signal": "positive",
        }
    ]
    db.add(
        LeadScore(
            lead_id=lead.id,
            score=30,
            priority_level="cold",
            factors=factors,
            explanation="json round trip",
            recommended_next_action="enrich",
        )
    )
    db.commit()

    stored = db.query(LeadScore).filter(LeadScore.lead_id == lead.id).one()
    assert stored.factors == factors
    assert stored.conversion_probability is None
