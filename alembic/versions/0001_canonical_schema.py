"""Canonical SalesGenie AI schema (eight tables).

Revision ID: 0001_canonical_schema
Revises: None

This migration is written with explicit operations so it can be reviewed and
applied identically to PostgreSQL (canonical target) and SQLite (local tests).
It creates the eight tables verified against ``docs/SRS.md``:

    users, leads, company_insights, outreach_campaigns,
    lead_scores, sales_interactions, crm_sync_logs, sales_analytics

Downgrade drops them in reverse dependency order.  It is destructive by design;
never run it against data you need.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_canonical_schema"
down_revision = None
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    # 1. users ------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 2. leads ------------------------------------------------------------
    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("company_name", sa.String(length=240), nullable=False),
        sa.Column("industry", sa.String(length=160), nullable=False),
        sa.Column("contact_name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("email_key", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=80), nullable=False),
        sa.Column("website", sa.String(length=500), nullable=False),
        sa.Column("company_size", sa.String(length=100), nullable=False),
        sa.Column("annual_revenue", sa.String(length=100), nullable=False),
        sa.Column("funding_stage", sa.String(length=100), nullable=False),
        sa.Column("tech_stack", sa.Text(), nullable=False),
        sa.Column("company_description", sa.Text(), nullable=False),
        sa.Column("prospect_role", sa.String(length=120), nullable=False),
        sa.Column("engagement_history", sa.Text(), nullable=False),
        sa.Column("explicit_needs", sa.Text(), nullable=False),
        sa.Column("response_behavior", sa.Text(), nullable=False),
        sa.Column("user_research", sa.Text(), nullable=False),
        sa.Column("pain_points", sa.Text(), nullable=False),
        sa.Column("lead_source", sa.String(length=120), nullable=False),
        sa.Column("lifecycle_stage", sa.String(length=32), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_leads_company_name", "leads", ["company_name"], unique=False)
    op.create_index("ix_leads_industry", "leads", ["industry"], unique=False)
    op.create_index("ix_leads_email_key", "leads", ["email_key"], unique=True)
    op.create_index("ix_leads_lifecycle_stage", "leads", ["lifecycle_stage"], unique=False)
    op.create_index("ix_leads_owner_id", "leads", ["owner_id"], unique=False)
    op.create_index(
        "ix_leads_stage_created", "leads", ["lifecycle_stage", "created_at"], unique=False
    )
    op.create_index(
        "ix_leads_company_contact", "leads", ["company_name", "contact_name"], unique=False
    )

    # 3. company_insights -------------------------------------------------
    op.create_table(
        "company_insights",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("business_needs", sa.JSON(), nullable=False),
        sa.Column("opportunities", sa.JSON(), nullable=False),
        sa.Column("pain_points", sa.JSON(), nullable=False),
        sa.Column("industry_context", sa.Text(), nullable=False),
        sa.Column("qualification", sa.JSON(), nullable=False),
        sa.Column("recommended_value_proposition", sa.Text(), nullable=False),
        sa.Column("discovery_questions", sa.JSON(), nullable=False),
        sa.Column("missing_information", sa.JSON(), nullable=False),
        sa.Column("supporting_evidence", sa.JSON(), nullable=False),
        sa.Column("provider", sa.String(length=60), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_company_insights_lead_id", "company_insights", ["lead_id"], unique=False
    )
    op.create_index(
        "ix_company_insights_lead_created",
        "company_insights",
        ["lead_id", "created_at"],
        unique=False,
    )

    # 4. outreach_campaigns -----------------------------------------------
    op.create_table(
        "outreach_campaigns",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("channel", sa.String(length=60), nullable=False),
        sa.Column("tone", sa.String(length=60), nullable=False),
        sa.Column("length", sa.String(length=40), nullable=False),
        sa.Column("outreach_type", sa.String(length=60), nullable=False),
        sa.Column("goal", sa.String(length=200), nullable=False),
        sa.Column("industry_context", sa.Text(), nullable=False),
        sa.Column("pain_points_used", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=60), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_outreach_campaigns_lead_id", "outreach_campaigns", ["lead_id"], unique=False
    )
    op.create_index(
        "ix_outreach_campaigns_status", "outreach_campaigns", ["status"], unique=False
    )
    op.create_index(
        "ix_outreach_lead_status",
        "outreach_campaigns",
        ["lead_id", "status"],
        unique=False,
    )

    # 5. lead_scores ------------------------------------------------------
    op.create_table(
        "lead_scores",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("conversion_probability", sa.Float(), nullable=True),
        sa.Column("priority_level", sa.String(length=20), nullable=False),
        sa.Column("fit_score", sa.Integer(), nullable=False),
        sa.Column("intent_score", sa.Integer(), nullable=False),
        sa.Column("engagement_score", sa.Integer(), nullable=False),
        sa.Column("decision_readiness_score", sa.Integer(), nullable=False),
        sa.Column("factors", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("recommended_next_action", sa.Text(), nullable=False),
        sa.Column("model_version", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_lead_scores_lead_id", "lead_scores", ["lead_id"], unique=False)
    op.create_index("ix_lead_scores_score", "lead_scores", ["score"], unique=False)
    op.create_index(
        "ix_lead_scores_lead_created", "lead_scores", ["lead_id", "created_at"], unique=False
    )
    op.create_index(
        "ix_lead_scores_score_prob",
        "lead_scores",
        ["score", "conversion_probability"],
        unique=False,
    )

    # 6. sales_interactions ----------------------------------------------
    op.create_table(
        "sales_interactions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("interaction_type", sa.String(length=60), nullable=False),
        sa.Column("interaction_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("key_points", sa.JSON(), nullable=False),
        sa.Column("action_items", sa.JSON(), nullable=False),
        sa.Column("follow_up_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sentiment", sa.String(length=40), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_sales_interactions_lead_id", "sales_interactions", ["lead_id"], unique=False
    )
    op.create_index(
        "ix_sales_interactions_lead_date",
        "sales_interactions",
        ["lead_id", "interaction_date"],
        unique=False,
    )

    # 7. crm_sync_logs ----------------------------------------------------
    op.create_table(
        "crm_sync_logs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("operation", sa.String(length=40), nullable=False),
        sa.Column("external_record_id", sa.String(length=240), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("request_metadata", sa.JSON(), nullable=False),
        sa.Column("response_metadata", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_crm_sync_logs_lead_id", "crm_sync_logs", ["lead_id"], unique=False)
    op.create_index("ix_crm_sync_logs_status", "crm_sync_logs", ["status"], unique=False)
    op.create_index(
        "ix_crm_sync_provider_status",
        "crm_sync_logs",
        ["provider", "status"],
        unique=False,
    )

    # 8. sales_analytics --------------------------------------------------
    op.create_table(
        "sales_analytics",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("metric_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_leads", sa.Integer(), nullable=False),
        sa.Column("qualified_leads", sa.Integer(), nullable=False),
        sa.Column("converted_leads", sa.Integer(), nullable=False),
        sa.Column("conversion_rate", sa.Float(), nullable=True),
        sa.Column("pipeline_value", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("average_lead_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_sales_analytics_metric_date", "sales_analytics", ["metric_date"], unique=False
    )


def downgrade() -> None:
    op.drop_table("sales_analytics")
    op.drop_table("crm_sync_logs")
    op.drop_table("sales_interactions")
    op.drop_table("lead_scores")
    op.drop_table("outreach_campaigns")
    op.drop_table("company_insights")
    op.drop_table("leads")
    op.drop_table("users")
