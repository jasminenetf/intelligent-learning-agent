"""Persisted generated resource artifacts from orchestrated jobs."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class ResourceArtifact(SQLModel, table=True):
    __tablename__ = "resource_artifacts"

    id: Optional[int] = Field(default=None, primary_key=True)
    artifact_id: str = Field(index=True, unique=True)
    job_id: str = Field(index=True)
    user_id: int = Field(index=True)
    course_id: int = Field(index=True)
    topic: str
    resource_type: str = Field(index=True)
    title: str
    content: str = Field(default="")
    quality_score: float = Field(default=0.0)
    metadata_json: Optional[str] = Field(default=None)
    download_resource_id: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
