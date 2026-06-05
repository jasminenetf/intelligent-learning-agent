"""Knowledge chunk model."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class KnowledgeChunk(SQLModel, table=True):
    __tablename__ = "knowledge_chunks"

    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="courses.id", index=True)
    file_id: int = Field(foreign_key="course_files.id")
    chunk_index: int = 0
    content: str
    source: str = ""
    page_number: Optional[int] = Field(default=None)
    token_count: Optional[int] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
