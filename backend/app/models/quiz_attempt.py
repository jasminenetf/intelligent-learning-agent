"""Quiz attempt model — records every quiz answer for learning evaluation."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class QuizAttempt(SQLModel, table=True):
    __tablename__ = "quiz_attempts"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    course_id: int = Field(default=0)
    topic: str = Field(default="")
    question_text: str
    selected_answer: str
    correct_answer: str
    is_correct: bool = False
    knowledge_point: str = Field(default="")
    explanation: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
