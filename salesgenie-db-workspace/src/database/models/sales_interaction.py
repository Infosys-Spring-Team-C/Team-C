from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from src.database.models.base import Base

class SalesInteraction(Base):
    """
    Stores logs and summaries of sales meetings, calls, and email conversations.
    Maps to the 'sales_interactions' table.
    """
    __tablename__ = "sales_interactions"

    interaction_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    lead_id = Column(
        Integer,
        ForeignKey("leads.lead_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    interaction_type = Column(
        String(50),
        nullable=False,
        doc="Type of interaction: Meeting, Call, Demo, Email, Note"
    )
    summary = Column(Text, nullable=True, doc="AI generated conversation summary")
    action_items = Column(Text, nullable=True, doc="Extracted follow-up tasks and action items")
    interaction_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    lead = relationship("Lead", back_populates="interactions")

    def __repr__(self):
        return f"<SalesInteraction(interaction_id={self.interaction_id}, type='{self.interaction_type}')>"
