import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

# Read database URL from environment; default to local SQLite for seamless dev
raw_db_url = os.getenv("DATABASE_URL", "").strip()

def get_engine():
    if raw_db_url and raw_db_url.startswith("postgresql"):
        try:
            # Test PostgreSQL connection with a short timeout
            pg_engine = create_engine(raw_db_url, connect_args={"connect_timeout": 3})
            with pg_engine.connect():
                return pg_engine
        except Exception as e:
            print(f"[Database] PostgreSQL connection failed ({e}). Falling back to SQLite development database.")
    
    # SQLite fallback (dev mode) - use absolute path to project directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_file = os.path.join(base_dir, "salesgenie.db")
    sqlite_url = f"sqlite:///{db_file}"
    return create_engine(sqlite_url, connect_args={"check_same_thread": False})

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
