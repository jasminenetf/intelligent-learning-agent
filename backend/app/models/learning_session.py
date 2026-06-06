"""Learning session model — persists commercial-grade tutoring conversations."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class LearningSession(SQLModel, table=True):
    __tablename__ = "learning_sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    course_id: int = Field(default=0, index=True)
    title: str = Field(default="新的学习会话", index=True)
    topic: Optional[str] = Field(default=None, index=True)
    summary: Optional[str] = Field(default=None)
    status: str = Field(default="active", index=True)
    last_message_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    message_count: int = Field(default=0)
    session_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column("metadata", JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="learning_sessions.id", index=True)
    role: str = Field(index=True)
    content: str
    message_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column("metadata", JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
