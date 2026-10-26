"""
SalesGenie AI - Database Module
Provides database connection engine, session management, and SQLAlchemy models.
"""
from src.database.connection import get_db, engine, SessionLocal
from src.database.models import (
    Base,
    User,
    Lead,
    LeadScore,
    CompanyInsight,
    OutreachCampaign,
    SalesInteraction,
    CRMSyncLog,
    SalesAnalytics,
)

__all__ = [
    "get_db",
    "engine",
    "SessionLocal",
    "Base",
    "User",
    "Lead",
    "LeadScore",
    "CompanyInsight",
    "OutreachCampaign",
    "SalesInteraction",
    "CRMSyncLog",
    "SalesAnalytics",
]
