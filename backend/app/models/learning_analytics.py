"""Learning analytics models for commercial learning product."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class LearningProgress(SQLModel, table=True):
    __tablename__ = "learning_progress"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    course_id: int = Field(foreign_key="courses.id", index=True)
    completed_lessons: int = Field(default=0)
    total_lessons: int = Field(default=0)
    completed_rate: float = Field(default=0.0)
    weak_points: Optional[str] = Field(default=None)
    next_recommendation: Optional[str] = Field(default=None)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, index=True)
    action: str = Field(index=True)
    target_type: Optional[str] = Field(default=None, index=True)
    target_id: Optional[str] = Field(default=None, index=True)
    detail: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)


class ResourceBookmark(SQLModel, table=True):
    __tablename__ = "resource_bookmarks"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    resource_id: str = Field(index=True)
    title: str = Field(default="")
    shared_token: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
