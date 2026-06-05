"""Course file model."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class CourseFile(SQLModel, table=True):
    __tablename__ = "course_files"

    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="courses.id", index=True)
    uploader_id: int = Field(foreign_key="users.id")
    original_filename: str
    stored_path: str
    content_type: str = ""
    file_ext: str = ""
    file_size: int = 0
    status: str = Field(default="uploaded")
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
