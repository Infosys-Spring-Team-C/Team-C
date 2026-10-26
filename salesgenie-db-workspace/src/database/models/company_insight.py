from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from src.database.models.base import Base

class CompanyInsight(Base):
    """
    Stores AI-generated intelligence about a lead's company, industry, and opportunities.
    Maps to the 'company_insights' table.
    """
    __tablename__ = "company_insights"

    insight_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    lead_id = Column(
        Integer,
        ForeignKey("leads.lead_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    business_needs = Column(Text, nullable=True, doc="Identified pain points and business needs")
    opportunities = Column(Text, nullable=True, doc="Sales and expansion opportunities")
    industry_analysis = Column(Text, nullable=True, doc="AI analysis of industry trends and competitors")
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    lead = relationship("Lead", back_populates="insights")

    def __repr__(self):
        return f"<CompanyInsight(insight_id={self.insight_id}, lead_id={self.lead_id})>"
