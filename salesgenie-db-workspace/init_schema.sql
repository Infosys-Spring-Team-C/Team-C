-- ====================================================================
-- SalesGenie AI - PostgreSQL Database Schema Initialization
-- Eight-Table Relational Schema based on Project Architecture
-- ====================================================================

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(50) NOT NULL,
    department VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);

-- 2. Leads Table (Central Entity)
CREATE TABLE IF NOT EXISTS leads (
    lead_id SERIAL PRIMARY KEY,
    company_name VARCHAR(150) NOT NULL,
    industry VARCHAR(100),
    contact_name VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(50),
    lead_status VARCHAR(50) DEFAULT 'New' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_leads_company_name ON leads(company_name);
CREATE INDEX IF NOT EXISTS ix_leads_industry ON leads(industry);
CREATE INDEX IF NOT EXISTS ix_leads_lead_status ON leads(lead_status);

-- 3. Lead_Scores Table (Assigned Responsibility)
CREATE TABLE IF NOT EXISTS lead_scores (
    score_id SERIAL PRIMARY KEY,
    lead_id INTEGER NOT NULL REFERENCES leads(lead_id) ON DELETE CASCADE,
    lead_score DOUBLE PRECISION NOT NULL,
    conversion_probability DOUBLE PRECISION NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_lead_scores_lead_id ON lead_scores(lead_id);
CREATE INDEX IF NOT EXISTS ix_lead_scores_lead_score ON lead_scores(lead_score);
CREATE INDEX IF NOT EXISTS ix_lead_scores_score_prob ON lead_scores(lead_score, conversion_probability);

-- 4. Company_Insights Table
CREATE TABLE IF NOT EXISTS company_insights (
    insight_id SERIAL PRIMARY KEY,
    lead_id INTEGER NOT NULL REFERENCES leads(lead_id) ON DELETE CASCADE,
    business_needs TEXT,
    opportunities TEXT,
    industry_analysis TEXT,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_company_insights_lead_id ON company_insights(lead_id);

-- 5. Outreach_Campaigns Table (Assigned Responsibility)
CREATE TABLE IF NOT EXISTS outreach_campaigns (
    campaign_id SERIAL PRIMARY KEY,
    lead_id INTEGER NOT NULL REFERENCES leads(lead_id) ON DELETE CASCADE,
    email_subject VARCHAR(255) NOT NULL,
    email_content TEXT NOT NULL,
    campaign_status VARCHAR(50) DEFAULT 'Draft' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_outreach_campaigns_lead_id ON outreach_campaigns(lead_id);
CREATE INDEX IF NOT EXISTS ix_outreach_campaigns_status ON outreach_campaigns(campaign_status);
CREATE INDEX IF NOT EXISTS ix_outreach_lead_status ON outreach_campaigns(lead_id, campaign_status);

-- 6. Sales_Interactions Table
CREATE TABLE IF NOT EXISTS sales_interactions (
    interaction_id SERIAL PRIMARY KEY,
    lead_id INTEGER NOT NULL REFERENCES leads(lead_id) ON DELETE CASCADE,
    interaction_type VARCHAR(50) NOT NULL,
    summary TEXT,
    action_items TEXT,
    interaction_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_sales_interactions_lead_id ON sales_interactions(lead_id);

-- 7. CRM_Sync_Logs Table
CREATE TABLE IF NOT EXISTS crm_sync_logs (
    sync_id SERIAL PRIMARY KEY,
    lead_id INTEGER NOT NULL REFERENCES leads(lead_id) ON DELETE CASCADE,
    crm_platform VARCHAR(50) NOT NULL,
    sync_status VARCHAR(50) DEFAULT 'Pending' NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_crm_sync_logs_lead_id ON crm_sync_logs(lead_id);

-- 8. Sales_Analytics Table
CREATE TABLE IF NOT EXISTS sales_analytics (
    analytics_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    conversion_rate DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
    pipeline_value NUMERIC(15, 2) DEFAULT 0.00 NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_sales_analytics_user_id ON sales_analytics(user_id);
