"""
database.py
-----------
Database engine setup, session factory, and helper utilities.
Uses SQLite via SQLAlchemy for simple local deployment.
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from models import Base
from contextlib import contextmanager

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

DB_PATH = os.environ.get("DB_PATH", "worldcup2026.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine (check_same_thread=False is needed for Streamlit's threaded model)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,           # Set to True to log all SQL (useful for debugging)
)

# Enable WAL mode for better concurrent read performance with SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ─────────────────────────────────────────────
# INITIALISATION
# ─────────────────────────────────────────────

def init_db():
    """
    Create all tables defined in models.py if they don't already exist.
    Call this once at app startup.
    """
    Base.metadata.create_all(bind=engine)


# ─────────────────────────────────────────────
# SESSION HELPERS
# ─────────────────────────────────────────────

@contextmanager
def get_db():
    """
    Context manager that yields a database session and ensures it is
    properly closed (and rolled back on error) when the block exits.

    Usage:
        with get_db() as db:
            db.query(User).all()
    """
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_session() -> Session:
    """
    Return a raw Session object for cases where a context manager is not
    convenient (e.g. long-lived Streamlit callbacks).
    Caller is responsible for committing and closing.
    """
    return SessionLocal()
