"""Initial migration creating all eight SalesGenie AI tables

Revision ID: 001_initial_eight_tables
Revises: 
Create Date: 2026-10-23 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial_eight_tables'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create 'users' table
    op.create_table(
        'users',
        sa.Column('user_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('department', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('user_id')
    )
    op.create_index(op.f('ix_users_user_id'), 'users', ['user_id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. Create 'leads' table
    op.create_table(
        'leads',
        sa.Column('lead_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('company_name', sa.String(length=150), nullable=False),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('contact_name', sa.String(length=100), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('lead_status', sa.String(length=50), server_default='New', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('lead_id')
    )
    op.create_index(op.f('ix_leads_lead_id'), 'leads', ['lead_id'], unique=False)
    op.create_index(op.f('ix_leads_company_name'), 'leads', ['company_name'], unique=False)
    op.create_index(op.f('ix_leads_industry'), 'leads', ['industry'], unique=False)
    op.create_index(op.f('ix_leads_email'), 'leads', ['email'], unique=False)
    op.create_index(op.f('ix_leads_lead_status'), 'leads', ['lead_status'], unique=False)

    # 3. Create 'lead_scores' table (Assigned Responsibility)
    op.create_table(
        'lead_scores',
        sa.Column('score_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('lead_id', sa.Integer(), nullable=False),
        sa.Column('lead_score', sa.Float(), nullable=False),
        sa.Column('conversion_probability', sa.Float(), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.lead_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('score_id')
    )
    op.create_index(op.f('ix_lead_scores_score_id'), 'lead_scores', ['score_id'], unique=False)
    op.create_index(op.f('ix_lead_scores_lead_id'), 'lead_scores', ['lead_id'], unique=False)
    op.create_index(op.f('ix_lead_scores_lead_score'), 'lead_scores', ['lead_score'], unique=False)
    op.create_index('ix_lead_scores_score_prob', 'lead_scores', ['lead_score', 'conversion_probability'], unique=False)

    # 4. Create 'company_insights' table
    op.create_table(
        'company_insights',
        sa.Column('insight_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('lead_id', sa.Integer(), nullable=False),
        sa.Column('business_needs', sa.Text(), nullable=True),
        sa.Column('opportunities', sa.Text(), nullable=True),
        sa.Column('industry_analysis', sa.Text(), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.lead_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('insight_id')
    )
    op.create_index(op.f('ix_company_insights_insight_id'), 'company_insights', ['insight_id'], unique=False)
    op.create_index(op.f('ix_company_insights_lead_id'), 'company_insights', ['lead_id'], unique=False)

    # 5. Create 'outreach_campaigns' table (Assigned Responsibility)
    op.create_table(
        'outreach_campaigns',
        sa.Column('campaign_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('lead_id', sa.Integer(), nullable=False),
        sa.Column('email_subject', sa.String(length=255), nullable=False),
        sa.Column('email_content', sa.Text(), nullable=False),
        sa.Column('campaign_status', sa.String(length=50), server_default='Draft', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.lead_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('campaign_id')
    )
    op.create_index(op.f('ix_outreach_campaigns_campaign_id'), 'outreach_campaigns', ['campaign_id'], unique=False)
    op.create_index(op.f('ix_outreach_campaigns_lead_id'), 'outreach_campaigns', ['lead_id'], unique=False)
    op.create_index(op.f('ix_outreach_campaigns_campaign_status'), 'outreach_campaigns', ['campaign_status'], unique=False)
    op.create_index('ix_outreach_lead_status', 'outreach_campaigns', ['lead_id', 'campaign_status'], unique=False)

    # 6. Create 'sales_interactions' table
    op.create_table(
        'sales_interactions',
        sa.Column('interaction_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('lead_id', sa.Integer(), nullable=False),
        sa.Column('interaction_type', sa.String(length=50), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('action_items', sa.Text(), nullable=True),
        sa.Column('interaction_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.lead_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('interaction_id')
    )
    op.create_index(op.f('ix_sales_interactions_interaction_id'), 'sales_interactions', ['interaction_id'], unique=False)
    op.create_index(op.f('ix_sales_interactions_lead_id'), 'sales_interactions', ['lead_id'], unique=False)

    # 7. Create 'crm_sync_logs' table
    op.create_table(
        'crm_sync_logs',
        sa.Column('sync_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('lead_id', sa.Integer(), nullable=False),
        sa.Column('crm_platform', sa.String(length=50), nullable=False),
        sa.Column('sync_status', sa.String(length=50), server_default='Pending', nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.lead_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('sync_id')
    )
    op.create_index(op.f('ix_crm_sync_logs_sync_id'), 'crm_sync_logs', ['sync_id'], unique=False)
    op.create_index(op.f('ix_crm_sync_logs_lead_id'), 'crm_sync_logs', ['lead_id'], unique=False)

    # 8. Create 'sales_analytics' table
    op.create_table(
        'sales_analytics',
        sa.Column('analytics_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('conversion_rate', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('pipeline_value', sa.Numeric(precision=15, scale=2), server_default='0.00', nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('analytics_id')
    )
    op.create_index(op.f('ix_sales_analytics_analytics_id'), 'sales_analytics', ['analytics_id'], unique=False)
    op.create_index(op.f('ix_sales_analytics_user_id'), 'sales_analytics', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order of creation to respect foreign key constraints
    op.drop_table('sales_analytics')
    op.drop_table('crm_sync_logs')
    op.drop_table('sales_interactions')
    op.drop_table('outreach_campaigns')
    op.drop_table('company_insights')
    op.drop_table('lead_scores')
    op.drop_table('leads')
    op.drop_table('users')
