from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from src.database.models.base import Base

class User(Base):
    """
    Represents sales representatives, managers, and system users.
    Maps to the 'users' table from the SalesGenie AI schema.
    """
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    role = Column(String(50), nullable=False)  # e.g., 'Sales Rep', 'Manager', 'Admin'
    department = Column(String(50), nullable=True)  # e.g., 'Outbound Sales', 'Enterprise'
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    analytics = relationship("SalesAnalytics", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, name='{self.name}', role='{self.role}')>"
