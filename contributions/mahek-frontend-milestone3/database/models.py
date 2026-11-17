from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database.connection import Base

class Lead(Base):
    __tablename__ = "leads"

    lead_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_name = Column(String(255), nullable=False)
    industry = Column(String(255), nullable=True)
    contact_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    company_size = Column(String(100), nullable=True)
    funding_stage = Column(String(100), nullable=True)
    business_need = Column(Text, nullable=True)
    lead_status = Column(String(50), default="New")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    insights = relationship("CompanyInsight", back_populates="lead", cascade="all, delete-orphan")
    scores = relationship("LeadScore", back_populates="lead", cascade="all, delete-orphan")
    campaigns = relationship("OutreachCampaign", back_populates="lead", cascade="all, delete-orphan")
    interactions = relationship("SalesInteraction", back_populates="lead", cascade="all, delete-orphan")


class CompanyInsight(Base):
    __tablename__ = "company_insights"

    insight_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.lead_id"), nullable=False)
    business_needs = Column(Text, nullable=True)
    opportunities = Column(Text, nullable=True)
    pain_points = Column(Text, nullable=True)
    industry_situation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="insights")


class LeadScore(Base):
    __tablename__ = "lead_scores"

    score_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.lead_id"), nullable=False)
    lead_score = Column(Integer, nullable=False)  # 0 - 100
    conversion_probability = Column(Float, nullable=False)  # 0.0 - 1.0 or %
    priority_level = Column(String(50), nullable=False)  # Very Hot / Hot / Warm / Cold
    reason = Column(Text, nullable=True)
    next_action = Column(Text, nullable=True)
    scoring_factors = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="scores")


class OutreachCampaign(Base):
    __tablename__ = "outreach_campaigns"

    campaign_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.lead_id"), nullable=False)
    email_subject = Column(String(255), nullable=False)
    email_content = Column(Text, nullable=False)
    follow_up_strategy = Column(Text, nullable=True)
    tone = Column(String(50), default="professional")
    status = Column(String(50), default="Draft")  # Draft / Sent
    created_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="campaigns")


class SalesInteraction(Base):
    __tablename__ = "sales_interactions"

    interaction_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.lead_id"), nullable=False)
    summary = Column(Text, nullable=True)
    action_items = Column(Text, nullable=True)
    key_points = Column(Text, nullable=True)
    follow_up = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="interactions")


class SalesAnalytics(Base):
    __tablename__ = "sales_analytics"

    analytics_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    total_leads = Column(Integer, default=0)
    hot_leads = Column(Integer, default=0)
    warm_leads = Column(Integer, default=0)
    cold_leads = Column(Integer, default=0)
    emails_sent = Column(Integer, default=0)
    calls_done = Column(Integer, default=0)
    conversion_rate = Column(Float, default=0.0)
    pipeline_value = Column(Float, default=0.0)
