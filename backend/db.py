from __future__ import annotations
import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Text, Integer, Float, DateTime, ForeignKey, JSON, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./salesgenie.db")
_opts = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_opts, pool_pre_ping=True)
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _record):
        cursor=dbapi_connection.cursor(); cursor.execute("PRAGMA foreign_keys=ON"); cursor.close()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

def utcnow(): return datetime.now(timezone.utc)

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class Lead(Base):
    __tablename__ = "leads"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(String(240), index=True)
    industry: Mapped[str] = mapped_column(String(160), default="")
    contact_name: Mapped[str] = mapped_column(String(200), default="")
    email: Mapped[str] = mapped_column(String(320), default="", index=True)
    phone: Mapped[str] = mapped_column(String(80), default="")
    company_website: Mapped[str] = mapped_column(String(500), default="")
    company_size: Mapped[str] = mapped_column(String(100), default="")
    annual_revenue: Mapped[str] = mapped_column(String(100), default="")
    funding_stage: Mapped[str] = mapped_column(String(100), default="")
    tech_stack: Mapped[str] = mapped_column(Text, default="")
    business_need: Mapped[str] = mapped_column(Text, default="")
    pain_points: Mapped[str] = mapped_column(Text, default="")
    lead_source: Mapped[str] = mapped_column(String(120), default="")
    lead_status: Mapped[str] = mapped_column(String(32), default="new", index=True)
    decision_maker_status: Mapped[str] = mapped_column(String(100), default="")
    engagement_level: Mapped[str] = mapped_column(String(40), default="unknown")
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class LeadScore(Base):
    __tablename__ = "lead_scores"
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    lead_score: Mapped[int] = mapped_column(Integer)
    conversion_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority_level: Mapped[str] = mapped_column(String(20), default="warm")
    fit_score: Mapped[int] = mapped_column(Integer, default=0); intent_score: Mapped[int] = mapped_column(Integer, default=0)
    engagement_score: Mapped[int] = mapped_column(Integer, default=0); decision_readiness_score: Mapped[int] = mapped_column(Integer, default=0)
    scoring_factors: Mapped[dict] = mapped_column(JSON, default=dict); explanation: Mapped[str] = mapped_column(Text, default="")
    model_version: Mapped[str] = mapped_column(String(80), default="heuristic-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class CompanyInsight(Base):
    __tablename__ = "company_insights"
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    business_needs: Mapped[list] = mapped_column(JSON, default=list); opportunities: Mapped[list] = mapped_column(JSON, default=list)
    pain_points: Mapped[list] = mapped_column(JSON, default=list); industry_context: Mapped[str] = mapped_column(Text, default="")
    recommended_value_proposition: Mapped[str] = mapped_column(Text, default="")
    supporting_evidence: Mapped[list] = mapped_column(JSON, default=list); provider: Mapped[str] = mapped_column(String(60), default="heuristic")
    model: Mapped[str] = mapped_column(String(120), default="deterministic-demo")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class OutreachCampaign(Base):
    __tablename__ = "outreach_campaigns"
    id: Mapped[int] = mapped_column(primary_key=True); lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    email_subject: Mapped[str] = mapped_column(String(500), default=""); email_content: Mapped[str] = mapped_column(Text, default="")
    tone: Mapped[str] = mapped_column(String(60), default="professional"); email_type: Mapped[str] = mapped_column(String(60), default="email")
    campaign_goal: Mapped[str] = mapped_column(String(200), default=""); pain_points_used: Mapped[list] = mapped_column(JSON, default=list)
    industry_context: Mapped[str] = mapped_column(Text, default=""); follow_up_strategy: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="draft"); provider: Mapped[str] = mapped_column(String(60), default="heuristic")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class SalesInteraction(Base):
    __tablename__ = "sales_interactions"
    id: Mapped[int] = mapped_column(primary_key=True); lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    interaction_type: Mapped[str] = mapped_column(String(60), default="call"); interaction_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    transcript: Mapped[str] = mapped_column(Text, default=""); summary: Mapped[str] = mapped_column(Text, default="")
    key_points: Mapped[list] = mapped_column(JSON, default=list); action_items: Mapped[list] = mapped_column(JSON, default=list)
    follow_up_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True); sentiment: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow); updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class SalesAnalytics(Base):
    __tablename__ = "sales_analytics"
    id: Mapped[int] = mapped_column(primary_key=True); user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    metric_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow); total_leads: Mapped[int] = mapped_column(Integer, default=0)
    qualified_leads: Mapped[int] = mapped_column(Integer, default=0); converted_leads: Mapped[int] = mapped_column(Integer, default=0)
    conversion_rate: Mapped[float | None] = mapped_column(Float, nullable=True); pipeline_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class CRMSyncLog(Base):
    __tablename__ = "crm_sync_logs"
    id: Mapped[int] = mapped_column(primary_key=True); lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id", ondelete="SET NULL"), nullable=True)
    provider: Mapped[str] = mapped_column(String(40)); entity_type: Mapped[str] = mapped_column(String(80), default="lead")
    operation: Mapped[str] = mapped_column(String(40)); external_record_id: Mapped[str] = mapped_column(String(240), default="")
    status: Mapped[str] = mapped_column(String(32), default="pending"); request_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    response_metadata: Mapped[dict] = mapped_column(JSON, default=dict); error_message: Mapped[str] = mapped_column(Text, default="")
    attempt_count: Mapped[int] = mapped_column(Integer, default=1); created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
