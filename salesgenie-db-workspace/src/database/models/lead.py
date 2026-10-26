from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from src.database.models.base import Base

class Lead(Base):
    """
    Central entity representing prospective customers and business accounts.
    Maps to the 'leads' table in the SalesGenie AI schema.
    """
    __tablename__ = "leads"

    lead_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    company_name = Column(String(150), nullable=False, index=True)
    industry = Column(String(100), nullable=True, index=True)
    contact_name = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    lead_status = Column(String(50), default="New", nullable=False, index=True)  # New, Contacted, Qualified, Lost, Converted
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships to child tables (1-to-many)
    scores = relationship("LeadScore", back_populates="lead", cascade="all, delete-orphan")
    insights = relationship("CompanyInsight", back_populates="lead", cascade="all, delete-orphan")
    campaigns = relationship("OutreachCampaign", back_populates="lead", cascade="all, delete-orphan")
    interactions = relationship("SalesInteraction", back_populates="lead", cascade="all, delete-orphan")
    crm_sync_logs = relationship("CRMSyncLog", back_populates="lead", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Lead(lead_id={self.lead_id}, company='{self.company_name}', status='{self.lead_status}')>"
