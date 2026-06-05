"""Student profile schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProfileExtractRequest(BaseModel):
    message: str = Field(..., min_length=1, description="自然语言描述（用于提取画像）")


class ProfileExtractResponse(BaseModel):
    major: Optional[str] = None
    learning_goal: Optional[str] = None
    knowledge_level: str = "intermediate"
    cognitive_style: str = "conceptual"
    weak_points: list[str] = []
    pace_preference: str = "moderate"
    resource_preference: list[str] = []
    motivation: Optional[str] = None
    meta_learning_level: str = "medium"
    confidence: float = 0.0
    raw_evidence: Optional[str] = None


class ProfileResponse(BaseModel):
    id: int
    user_id: int
    major: Optional[str] = None
    learning_goal: Optional[str] = None
    knowledge_level: str
    cognitive_style: str
    weak_points: Optional[str] = None
    pace_preference: str
    resource_preference: Optional[str] = None
    motivation: Optional[str] = None
    meta_learning_level: str
    emotion_tendency: Optional[str] = None
    raw_evidence: Optional[str] = None
    last_extracted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ProfileUpdateRequest(BaseModel):
    major: Optional[str] = None
    learning_goal: Optional[str] = None
    knowledge_level: Optional[str] = None
    cognitive_style: Optional[str] = None
    weak_points: Optional[str] = None
    pace_preference: Optional[str] = None
    resource_preference: Optional[str] = None
    motivation: Optional[str] = None
    meta_learning_level: Optional[str] = None
    emotion_tendency: Optional[str] = None
