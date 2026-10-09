"""
Database setup. Defaults to a local SQLite file (zero-config, good for
development). Set DATABASE_URL to point at Postgres in production, e.g.:

    DATABASE_URL=postgresql://user:password@host:5432/finguard
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./finguard.db")

# check_same_thread is only needed/valid for SQLite
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session per-request and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
