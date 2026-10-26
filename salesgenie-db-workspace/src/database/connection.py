import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load environment variables from .env file
load_dotenv()

# Read the database URL or construct a default fallback
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres_password@localhost:5432/salesgenie_db"
)

# Create the SQLAlchemy engine
# pool_pre_ping checks if connection is alive before using it
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "False").lower() == "true",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Session factory for generating database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Context manager / dependency for FastAPI or scripts.
    Yields a database session and ensures it closes when finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
