-- ============================================================================
-- SalesGenie AI - PostgreSQL schema baseline (canonical, eight tables)
--
-- GENERATED FILE - do not edit by hand.
-- Source of truth : backend/db.py (SQLAlchemy models)
-- Regenerate      : python scripts/render_db_workspace.py
-- Verify          : python scripts/render_db_workspace.py --check
--
-- The migration that builds the same schema in an existing database is
-- alembic/versions/0001_canonical_schema.py. This file is the portable
-- equivalent for a brand-new database (for example the Docker entrypoint).
-- ============================================================================

CREATE TABLE IF NOT EXISTS sales_analytics (
	id SERIAL NOT NULL, 
	metric_date TIMESTAMP WITH TIME ZONE NOT NULL, 
	total_leads INTEGER NOT NULL, 
	qualified_leads INTEGER NOT NULL, 
	converted_leads INTEGER NOT NULL, 
	conversion_rate FLOAT, 
	pipeline_value NUMERIC(15, 2), 
	average_lead_score FLOAT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS ix_sales_analytics_metric_date ON sales_analytics (metric_date);

CREATE TABLE IF NOT EXISTS users (
	id SERIAL NOT NULL, 
	email VARCHAR(320) NOT NULL, 
	full_name VARCHAR(200) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);

CREATE TABLE IF NOT EXISTS leads (
	id SERIAL NOT NULL, 
	company_name VARCHAR(240) NOT NULL, 
	industry VARCHAR(160) NOT NULL, 
	contact_name VARCHAR(200) NOT NULL, 
	email VARCHAR(320) NOT NULL, 
	email_key VARCHAR(320), 
	phone VARCHAR(80) NOT NULL, 
	website VARCHAR(500) NOT NULL, 
	company_size VARCHAR(100) NOT NULL, 
	annual_revenue VARCHAR(100) NOT NULL, 
	funding_stage VARCHAR(100) NOT NULL, 
	tech_stack TEXT NOT NULL, 
	company_description TEXT NOT NULL, 
	prospect_role VARCHAR(120) NOT NULL, 
	engagement_history TEXT NOT NULL, 
	explicit_needs TEXT NOT NULL, 
	response_behavior TEXT NOT NULL, 
	user_research TEXT NOT NULL, 
	pain_points TEXT NOT NULL, 
	lead_source VARCHAR(120) NOT NULL, 
	lifecycle_stage VARCHAR(32) NOT NULL, 
	owner_id INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_leads_company_contact ON leads (company_name, contact_name);
CREATE INDEX IF NOT EXISTS ix_leads_company_name ON leads (company_name);
CREATE UNIQUE INDEX IF NOT EXISTS ix_leads_email_key ON leads (email_key);
CREATE INDEX IF NOT EXISTS ix_leads_industry ON leads (industry);
CREATE INDEX IF NOT EXISTS ix_leads_lifecycle_stage ON leads (lifecycle_stage);
CREATE INDEX IF NOT EXISTS ix_leads_owner_id ON leads (owner_id);
CREATE INDEX IF NOT EXISTS ix_leads_stage_created ON leads (lifecycle_stage, created_at);

CREATE TABLE IF NOT EXISTS company_insights (
	id SERIAL NOT NULL, 
	lead_id INTEGER NOT NULL, 
	business_needs JSON NOT NULL, 
	opportunities JSON NOT NULL, 
	pain_points JSON NOT NULL, 
	industry_context TEXT NOT NULL, 
	qualification JSON NOT NULL, 
	recommended_value_proposition TEXT NOT NULL, 
	discovery_questions JSON NOT NULL, 
	missing_information JSON NOT NULL, 
	supporting_evidence JSON NOT NULL, 
	provider VARCHAR(60) NOT NULL, 
	model VARCHAR(120) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(lead_id) REFERENCES leads (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_company_insights_lead_created ON company_insights (lead_id, created_at);
CREATE INDEX IF NOT EXISTS ix_company_insights_lead_id ON company_insights (lead_id);

CREATE TABLE IF NOT EXISTS crm_sync_logs (
	id SERIAL NOT NULL, 
	lead_id INTEGER, 
	provider VARCHAR(40) NOT NULL, 
	entity_type VARCHAR(80) NOT NULL, 
	operation VARCHAR(40) NOT NULL, 
	external_record_id VARCHAR(240) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	request_metadata JSON NOT NULL, 
	response_metadata JSON NOT NULL, 
	error_message TEXT NOT NULL, 
	attempt_count INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(lead_id) REFERENCES leads (id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_crm_sync_logs_lead_id ON crm_sync_logs (lead_id);
CREATE INDEX IF NOT EXISTS ix_crm_sync_logs_status ON crm_sync_logs (status);
CREATE INDEX IF NOT EXISTS ix_crm_sync_provider_status ON crm_sync_logs (provider, status);

CREATE TABLE IF NOT EXISTS lead_scores (
	id SERIAL NOT NULL, 
	lead_id INTEGER NOT NULL, 
	score INTEGER NOT NULL, 
	conversion_probability FLOAT, 
	priority_level VARCHAR(20) NOT NULL, 
	fit_score INTEGER NOT NULL, 
	intent_score INTEGER NOT NULL, 
	engagement_score INTEGER NOT NULL, 
	decision_readiness_score INTEGER NOT NULL, 
	factors JSON NOT NULL, 
	explanation TEXT NOT NULL, 
	recommended_next_action TEXT NOT NULL, 
	model_version VARCHAR(80) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(lead_id) REFERENCES leads (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_lead_scores_lead_created ON lead_scores (lead_id, created_at);
CREATE INDEX IF NOT EXISTS ix_lead_scores_lead_id ON lead_scores (lead_id);
CREATE INDEX IF NOT EXISTS ix_lead_scores_score ON lead_scores (score);
CREATE INDEX IF NOT EXISTS ix_lead_scores_score_prob ON lead_scores (score, conversion_probability);

CREATE TABLE IF NOT EXISTS outreach_campaigns (
	id SERIAL NOT NULL, 
	lead_id INTEGER NOT NULL, 
	subject VARCHAR(500) NOT NULL, 
	body TEXT NOT NULL, 
	channel VARCHAR(60) NOT NULL, 
	tone VARCHAR(60) NOT NULL, 
	length VARCHAR(40) NOT NULL, 
	outreach_type VARCHAR(60) NOT NULL, 
	goal VARCHAR(200) NOT NULL, 
	industry_context TEXT NOT NULL, 
	pain_points_used JSON NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	provider VARCHAR(60) NOT NULL, 
	model VARCHAR(120) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(lead_id) REFERENCES leads (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_outreach_campaigns_lead_id ON outreach_campaigns (lead_id);
CREATE INDEX IF NOT EXISTS ix_outreach_campaigns_status ON outreach_campaigns (status);
CREATE INDEX IF NOT EXISTS ix_outreach_lead_status ON outreach_campaigns (lead_id, status);

CREATE TABLE IF NOT EXISTS sales_interactions (
	id SERIAL NOT NULL, 
	lead_id INTEGER NOT NULL, 
	interaction_type VARCHAR(60) NOT NULL, 
	interaction_date TIMESTAMP WITH TIME ZONE NOT NULL, 
	transcript TEXT NOT NULL, 
	summary TEXT NOT NULL, 
	key_points JSON NOT NULL, 
	action_items JSON NOT NULL, 
	follow_up_date TIMESTAMP WITH TIME ZONE, 
	sentiment VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(lead_id) REFERENCES leads (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_sales_interactions_lead_date ON sales_interactions (lead_id, interaction_date);
CREATE INDEX IF NOT EXISTS ix_sales_interactions_lead_id ON sales_interactions (lead_id);
