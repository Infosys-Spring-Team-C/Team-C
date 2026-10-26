from sqlalchemy import Column, Integer, Float, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from src.database.models.base import Base

class SalesAnalytics(Base):
    """
    Stores aggregated performance metrics, conversion rates, and pipeline values per sales user.
    Maps to the 'sales_analytics' table.
    """
    __tablename__ = "sales_analytics"

    analytics_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign Key referencing the sales rep or manager"
    )
    conversion_rate = Column(
        Float,
        default=0.0,
        nullable=False,
        doc="Team or representative conversion rate percentage (e.g., 24.8)"
    )
    pipeline_value = Column(
        Numeric(15, 2),
        default=0.00,
        nullable=False,
        doc="Monetary pipeline value in USD (e.g., 2400000.00 for $2.4M)"
    )
    generated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    # Relationships
    user = relationship("User", back_populates="analytics")

    def __repr__(self):
        return (
            f"<SalesAnalytics(analytics_id={self.analytics_id}, user_id={self.user_id}, "
            f"conv_rate={self.conversion_rate}%, pipeline={self.pipeline_value})>"
        )
