"""Resource generation job tracking."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class ResourceJob(SQLModel, table=True):
    __tablename__ = "resource_jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: str = Field(index=True, unique=True)
    user_id: int = Field(index=True)
    course_id: int = Field(index=True)
    topic: str
    resource_types: str = Field(default="[]", description="JSON list of resource types")
    status: str = Field(default="pending", index=True)
    progress: float = Field(default=0.0)
    current_agent: Optional[str] = Field(default=None)
    result_json: Optional[str] = Field(default=None)
    trace_json: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
