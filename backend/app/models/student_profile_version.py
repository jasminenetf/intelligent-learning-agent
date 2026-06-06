"""Student profile version snapshot model."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class StudentProfileVersion(SQLModel, table=True):
    __tablename__ = "student_profile_versions"

    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="student_profiles.id", index=True)
    version: int = Field(index=True)
    snapshot_json: str = Field(description="画像快照 JSON")
    trigger_source: str = Field(default="dialogue", description="触发来源: dialogue/quiz/behavior/manual")
    trigger_text: Optional[str] = Field(default=None, description="触发文本")
    confidence: float = Field(default=0.0, description="版本置信度")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
