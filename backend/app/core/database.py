"""Database engine and session management."""

import os
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _normalize_database_url(database_url: str) -> str:
    """Normalize database configuration to a SQLAlchemy URL.

    Supports:
    - a proper SQLAlchemy URL (e.g. sqlite:///./data/app.db)
    - a bare SQLite file path (e.g. C:\\path\\to\\app.db)
    - an empty value, which falls back to the project-root SQLite DB
    """
    default_db = (PROJECT_ROOT / "data" / "app.db").resolve()
    if not database_url:
        return f"sqlite:///{default_db.as_posix().lstrip('/')}"

    if database_url.startswith(("postgresql://", "mysql://", "mysql+pymysql://", "postgresql+psycopg2://")):
        return database_url

    if database_url.startswith("sqlite://"):
        raw_path = database_url.replace("sqlite:///", "", 1)
        db_path = Path(raw_path)
        if not db_path.is_absolute():
            db_path = (PROJECT_ROOT / db_path).resolve()
        else:
            db_path = db_path.resolve()
        return f"sqlite:///{db_path.as_posix().lstrip('/')}"

    db_path = Path(database_url)
    if not db_path.is_absolute():
        db_path = (PROJECT_ROOT / db_path).resolve()
    else:
        db_path = db_path.resolve()
    return f"sqlite:///{db_path.as_posix().lstrip('/')}"


DATABASE_URL = _normalize_database_url(settings.DATABASE_URL)

_data_dir = os.path.dirname(DATABASE_URL.replace("sqlite:///", ""))
if _data_dir and not os.path.exists(_data_dir):
    Path(_data_dir).mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False,
)


def _ensure_sqlite_columns():
    if not DATABASE_URL.startswith("sqlite"):
        return
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "student_profiles" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("student_profiles")}
        alters = []
        if "learning_stage" not in cols:
            alters.append("ALTER TABLE student_profiles ADD COLUMN learning_stage VARCHAR DEFAULT 'foundation'")
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
    SQLModel.metadata.create_all(engine)
    _ensure_sqlite_columns()


def get_session():
    with Session(engine) as session:
        yield session
