"""SQLAlchemy models and engine/session management.

The canonical schema has eight tables, verified against ``docs/SRS.md``
(entities ENT-01 .. ENT-07 plus a ``users`` table required by the JWT/RBAC
requirement NFR-005).  It is deliberately richer than the initial draft in
Sai Surekha's repository because Modules 2-4 require persisted outreach
parameters, explainable score factors and structured intelligence.

Schema changes must go through an Alembic migration; ``Base.metadata.create_all``
is only used by the test suite and the bootstrap CLI.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from backend.config import get_settings

# --------------------------------------------------------------------------
# Lifecycle vocabulary
# --------------------------------------------------------------------------
LIFECYCLE_STAGES: tuple[str, ...] = (
    "prospecting",
    "discovery",
    "qualified",
    "proposal",
    "negotiation",
    "converted",
    "lost",
)
TERMINAL_STAGES: frozenset[str] = frozenset({"converted", "lost"})

#: Legacy / UI aliases mapped onto the canonical stage names.
STAGE_ALIASES: dict[str, str] = {
    "new": "prospecting",
    "active": "discovery",
    "contacted": "discovery",
    "open": "discovery",
    "closed won": "converted",
    "won": "converted",
    "closed lost": "lost",
    "unqualified": "lost",
}

ROLES: tuple[str, ...] = ("admin", "manager", "rep", "viewer")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


def _build_engine(url: str):
    options: dict = {"pool_pre_ping": True, "future": True}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, **options)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _sqlite_foreign_keys(dbapi_connection, _record):  # pragma: no cover
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = _build_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def get_db():
    """FastAPI dependency yielding a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


# --------------------------------------------------------------------------
# 1. users
# --------------------------------------------------------------------------
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="rep", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<User(id={self.id}, email={self.email!r}, role={self.role!r})>"


# --------------------------------------------------------------------------
# 2. leads
# --------------------------------------------------------------------------
class Lead(Base, TimestampMixin):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_name: Mapped[str] = mapped_column(String(240), index=True, nullable=False)
    industry: Mapped[str] = mapped_column(String(160), default="", index=True, nullable=False)
    contact_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    email: Mapped[str] = mapped_column(String(320), default="", nullable=False)
    #: Lower-cased e-mail used for duplicate detection. Unique when present.
    email_key: Mapped[str | None] = mapped_column(
        String(320), unique=True, nullable=True, index=True
    )
    phone: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    website: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    company_size: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    annual_revenue: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    funding_stage: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    tech_stack: Mapped[str] = mapped_column(Text, default="", nullable=False)
    company_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    prospect_role: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    engagement_history: Mapped[str] = mapped_column(Text, default="", nullable=False)
    explicit_needs: Mapped[str] = mapped_column(Text, default="", nullable=False)
    response_behavior: Mapped[str] = mapped_column(Text, default="", nullable=False)
    user_research: Mapped[str] = mapped_column(Text, default="", nullable=False)
    pain_points: Mapped[str] = mapped_column(Text, default="", nullable=False)
    lead_source: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    lifecycle_stage: Mapped[str] = mapped_column(
        String(32), default="prospecting", index=True, nullable=False
    )
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    __table_args__ = (
        Index("ix_leads_stage_created", "lifecycle_stage", "created_at"),
        Index("ix_leads_company_contact", "company_name", "contact_name"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Lead(id={self.id}, company={self.company_name!r})>"


# --------------------------------------------------------------------------
# 3. company_insights
# --------------------------------------------------------------------------
class CompanyInsight(Base):
    __tablename__ = "company_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), index=True, nullable=False
    )
    business_needs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    opportunities: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    pain_points: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    industry_context: Mapped[str] = mapped_column(Text, default="", nullable=False)
    qualification: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    recommended_value_proposition: Mapped[str] = mapped_column(Text, default="", nullable=False)
    discovery_questions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    missing_information: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    supporting_evidence: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    provider: Mapped[str] = mapped_column(String(60), default="heuristic", nullable=False)
    model: Mapped[str] = mapped_column(String(120), default="deterministic-v1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    __table_args__ = (
        Index("ix_company_insights_lead_created", "lead_id", "created_at"),
    )


# --------------------------------------------------------------------------
# 4. outreach_campaigns
# --------------------------------------------------------------------------
class OutreachCampaign(Base, TimestampMixin):
    __tablename__ = "outreach_campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), index=True, nullable=False
    )
    subject: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    channel: Mapped[str] = mapped_column(String(60), default="email", nullable=False)
    tone: Mapped[str] = mapped_column(String(60), default="professional", nullable=False)
    length: Mapped[str] = mapped_column(String(40), default="medium", nullable=False)
    outreach_type: Mapped[str] = mapped_column(String(60), default="cold_email", nullable=False)
    goal: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    industry_context: Mapped[str] = mapped_column(Text, default="", nullable=False)
    pain_points_used: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="draft", index=True, nullable=False
    )
    provider: Mapped[str] = mapped_column(String(60), default="heuristic", nullable=False)
    model: Mapped[str] = mapped_column(String(120), default="deterministic-v1", nullable=False)

    __table_args__ = (
        Index("ix_outreach_lead_status", "lead_id", "status"),
    )


# --------------------------------------------------------------------------
# 5. lead_scores
# --------------------------------------------------------------------------
class LeadScore(Base):
    __tablename__ = "lead_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), index=True, nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    conversion_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority_level: Mapped[str] = mapped_column(String(20), default="warm", nullable=False)
    fit_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    intent_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    engagement_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    decision_readiness_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    factors: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    recommended_next_action: Mapped[str] = mapped_column(Text, default="", nullable=False)
    model_version: Mapped[str] = mapped_column(
        String(80), default="heuristic-v1", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    __table_args__ = (
        Index("ix_lead_scores_lead_created", "lead_id", "created_at"),
        Index("ix_lead_scores_score_prob", "score", "conversion_probability"),
    )


# --------------------------------------------------------------------------
# 6. sales_interactions
# --------------------------------------------------------------------------
class SalesInteraction(Base, TimestampMixin):
    __tablename__ = "sales_interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), index=True, nullable=False
    )
    interaction_type: Mapped[str] = mapped_column(String(60), default="call", nullable=False)
    interaction_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    transcript: Mapped[str] = mapped_column(Text, default="", nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    key_points: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    action_items: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    follow_up_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sentiment: Mapped[str] = mapped_column(String(40), default="", nullable=False)

    __table_args__ = (
        Index("ix_sales_interactions_lead_date", "lead_id", "interaction_date"),
    )


# --------------------------------------------------------------------------
# 7. crm_sync_logs
# --------------------------------------------------------------------------
class CRMSyncLog(Base, TimestampMixin):
    __tablename__ = "crm_sync_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int | None] = mapped_column(
        ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), default="lead", nullable=False)
    operation: Mapped[str] = mapped_column(String(40), default="upsert", nullable=False)
    external_record_id: Mapped[str] = mapped_column(String(240), default="", nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="pending", index=True, nullable=False
    )
    request_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    response_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    __table_args__ = (
        Index("ix_crm_sync_provider_status", "provider", "status"),
    )


# --------------------------------------------------------------------------
# 8. sales_analytics
# --------------------------------------------------------------------------
class SalesAnalytics(Base):
    __tablename__ = "sales_analytics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    metric_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True, nullable=False
    )
    total_leads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    qualified_leads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    converted_leads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    conversion_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    pipeline_value: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    average_lead_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


def init_db() -> None:
    """Create tables from metadata. Used by the CLI and tests only.

    Production/deployment path is ``alembic upgrade head``.
    """
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:  # pragma: no cover - destructive, tests/CLI only
    Base.metadata.drop_all(bind=engine)
