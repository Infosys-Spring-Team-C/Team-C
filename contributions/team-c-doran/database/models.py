"""SQLAlchemy models for SalesGenie AI."""

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for declarative SQLAlchemy models."""


class Lead(Base):
    """A sales lead tracked by the SalesGenie platform."""

    __tablename__ = "leads"

    lead_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    industry: Mapped[str] = mapped_column(String, nullable=False)
    contact_name: Mapped[str] = mapped_column(String, nullable=False)
    lead_status: Mapped[str] = mapped_column(
        String, nullable=False, default="new", server_default="new", index=True
    )
    tech_stack: Mapped[str | None] = mapped_column(Text, nullable=True)
    funding_stage: Mapped[str | None] = mapped_column(String, nullable=True)
    company_size: Mapped[str | None] = mapped_column(String, nullable=True)
    revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class OutreachCampaign(Base):
    """An outreach email campaign generated for a lead."""

    __tablename__ = "outreach_campaigns"

    campaign_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.lead_id", ondelete="CASCADE"), nullable=False, index=True
    )
    email_subject: Mapped[str] = mapped_column(String, nullable=False)
    email_content: Mapped[str] = mapped_column(Text, nullable=False)
    follow_up_strategy: Mapped[str] = mapped_column(Text, nullable=False)
    tone: Mapped[str] = mapped_column(String, nullable=False, default="professional")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )


class LeadScore(Base):
    """Current calculated score card for a lead."""

    __tablename__ = "lead_scores"
    __table_args__ = (UniqueConstraint("lead_id", name="uq_lead_scores_lead_id"),)

    score_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.lead_id", ondelete="CASCADE"), nullable=False, index=True
    )
    lead_score: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    conversion_probability: Mapped[float] = mapped_column(Float, nullable=False)
    priority_level: Mapped[str] = mapped_column(String, nullable=False, index=True)
    scoring_factors: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )


class CRMSyncLog(Base):
    """Audit record for a lead synchronization attempt with a CRM provider."""

    __tablename__ = "crm_sync_logs"

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.lead_id", ondelete="CASCADE"), nullable=False, index=True
    )
    crm_provider: Mapped[str] = mapped_column(String, nullable=False, index=True)
    sync_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        index=True,
    )
