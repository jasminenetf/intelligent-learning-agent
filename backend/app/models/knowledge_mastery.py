"""Knowledge mastery model for per-point learning progress."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class KnowledgeMastery(SQLModel, table=True):
    __tablename__ = "knowledge_mastery"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="users.id")
    course_id: int = Field(index=True, foreign_key="courses.id")
    knowledge_point: str = Field(index=True, description="知识点名称")
    mastery_score: float = Field(default=0.5, description="掌握度 0-1")
    attempt_count: int = Field(default=0, description="作答次数")
    correct_count: int = Field(default=0, description="正确次数")
    wrong_count: int = Field(default=0, description="错误次数")
    last_practiced_at: Optional[datetime] = Field(default=None)
    recommended_action: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
