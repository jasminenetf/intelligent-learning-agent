"""Database engine and session management."""

import os
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

# Ensure data directory exists
_data_dir = os.path.dirname(settings.DATABASE_URL.replace("sqlite:///", ""))
if _data_dir and not os.path.exists(_data_dir):
    Path(_data_dir).mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


def create_db_and_tables():
    """Create all tables defined by SQLModel metadata."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Yield a database session."""
    with Session(engine) as session:
        yield session
