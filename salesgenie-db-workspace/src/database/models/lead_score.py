from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import relationship
from src.database.models.base import Base

class LeadScore(Base):
    """
    Stores AI-predicted qualification scores and conversion probabilities for leads.
    Assigned DevOps responsibility: includes optimized foreign keys and indexes.
    Maps to the 'lead_scores' table.
    """
    __tablename__ = "lead_scores"

    score_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    lead_id = Column(
        Integer,
        ForeignKey("leads.lead_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign Key referencing the evaluated lead in leads table"
    )
    lead_score = Column(
        Float,
        nullable=False,
        index=True,
        doc="AI Qualification score (e.g., 0.0 to 100.0) used for sorting leads"
    )
    conversion_probability = Column(
        Float,
        nullable=False,
        doc="AI predicted conversion probability (0.00 to 1.00)"
    )
    generated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        doc="Timestamp when the AI model generated this score"
    )

    # Relationships
    lead = relationship("Lead", back_populates="scores")

    # Table arguments: composite index for leaderboard queries
    __table_args__ = (
        Index("ix_lead_scores_score_prob", "lead_score", "conversion_probability"),
    )

    def __repr__(self):
        return (
            f"<LeadScore(score_id={self.score_id}, lead_id={self.lead_id}, "
            f"score={self.lead_score}, prob={self.conversion_probability})>"
        )
