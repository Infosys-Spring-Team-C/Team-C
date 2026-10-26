from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import relationship
from src.database.models.base import Base

class OutreachCampaign(Base):
    """
    Stores AI-generated personalized outreach emails, messages, and follow-ups.
    Assigned DevOps responsibility: includes optimized foreign keys and indexes.
    Maps to the 'outreach_campaigns' table.
    """
    __tablename__ = "outreach_campaigns"

    campaign_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    lead_id = Column(
        Integer,
        ForeignKey("leads.lead_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign Key referencing the target lead"
    )
    email_subject = Column(String(255), nullable=False, doc="AI generated email subject line")
    email_content = Column(Text, nullable=False, doc="AI generated personalized email body")
    campaign_status = Column(
        String(50),
        default="Draft",
        nullable=False,
        index=True,
        doc="Lifecycle state: Draft, Scheduled, Sent, Opened, Replied, Bounced"
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    # Relationships
    lead = relationship("Lead", back_populates="campaigns")

    # Table arguments: composite index for filtering campaigns by lead and status
    __table_args__ = (
        Index("ix_outreach_lead_status", "lead_id", "campaign_status"),
    )

    def __repr__(self):
        return (
            f"<OutreachCampaign(campaign_id={self.campaign_id}, lead_id={self.lead_id}, "
            f"status='{self.campaign_status}')>"
        )
