"""Student profile field-level change log."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class StudentProfileChangeLog(SQLModel, table=True):
    __tablename__ = "student_profile_change_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="student_profiles.id", index=True)
    field_name: str = Field(index=True)
    old_value: Optional[str] = Field(default=None)
    new_value: Optional[str] = Field(default=None)
    reason: Optional[str] = Field(default=None)
    source_type: str = Field(default="dialogue")
    source_id: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
