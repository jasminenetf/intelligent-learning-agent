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


def _ensure_sqlite_columns():
    """Add new columns to existing SQLite tables (lightweight migration)."""
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "student_profiles" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("student_profiles")}
        alters = []
        if "learning_stage" not in cols:
            alters.append(
                "ALTER TABLE student_profiles ADD COLUMN learning_stage VARCHAR DEFAULT 'foundation'"
            )
        for col, ddl in (
            ("profile_source", "ALTER TABLE student_profiles ADD COLUMN profile_source VARCHAR"),
            ("profile_version", "ALTER TABLE student_profiles ADD COLUMN profile_version INTEGER DEFAULT 1"),
            ("profile_confidence", "ALTER TABLE student_profiles ADD COLUMN profile_confidence FLOAT DEFAULT 0.0"),
            ("last_extracted_at", "ALTER TABLE student_profiles ADD COLUMN last_extracted_at DATETIME"),
            ("emotion_tendency", "ALTER TABLE student_profiles ADD COLUMN emotion_tendency VARCHAR"),
            ("meta_learning_level", "ALTER TABLE student_profiles ADD COLUMN meta_learning_level VARCHAR DEFAULT 'medium'"),
            ("resource_preference", "ALTER TABLE student_profiles ADD COLUMN resource_preference VARCHAR"),
            ("motivation", "ALTER TABLE student_profiles ADD COLUMN motivation VARCHAR"),
            ("raw_evidence", "ALTER TABLE student_profiles ADD COLUMN raw_evidence VARCHAR"),
        ):
            if col not in cols:
                alters.append(ddl)
        if alters:
            with engine.begin() as conn:
                for stmt in alters:
                    conn.execute(text(stmt))


def create_db_and_tables():
    """Create all tables defined by SQLModel metadata."""
    SQLModel.metadata.create_all(engine)
    _ensure_sqlite_columns()


def get_session():
    """Yield a database session."""
    with Session(engine) as session:
        yield session
