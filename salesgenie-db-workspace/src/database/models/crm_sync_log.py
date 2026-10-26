from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from src.database.models.base import Base

class CRMSyncLog(Base):
    """
    Tracks synchronization status between SalesGenie AI and external CRM platforms.
    Maps to the 'crm_sync_logs' table.
    """
    __tablename__ = "crm_sync_logs"

    sync_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    lead_id = Column(
        Integer,
        ForeignKey("leads.lead_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    crm_platform = Column(
        String(50),
        nullable=False,
        doc="Target CRM system, e.g., Salesforce, HubSpot, Zoho"
    )
    sync_status = Column(
        String(50),
        nullable=False,
        default="Pending",
        doc="Sync status: Success, Failed, Pending, In_Progress"
    )
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    lead = relationship("Lead", back_populates="crm_sync_logs")

    def __repr__(self):
        return f"<CRMSyncLog(sync_id={self.sync_id}, platform='{self.crm_platform}', status='{self.sync_status}')>"
