"""Student profile model — 6+ dimensions of learner characteristics."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class StudentProfile(SQLModel, table=True):
    __tablename__ = "student_profiles"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True, index=True)

    # Core 6 dimensions
    major: Optional[str] = Field(default=None, description="专业/学科")
    learning_goal: Optional[str] = Field(default=None, description="学习目标")
    knowledge_level: str = Field(default="intermediate", description="知识基础: beginner/intermediate/advanced")
    cognitive_style: str = Field(default="conceptual", description="认知风格: conceptual/logical/practice_oriented")
    weak_points: Optional[str] = Field(default=None, description="知识短板/易错点 (JSON list)")
    pace_preference: str = Field(default="moderate", description="学习节奏: slow/moderate/fast")
    learning_stage: str = Field(
        default="foundation",
        description="学习阶段: foundation/consolidating/practice/review/advanced",
    )

    # Extended dimensions
    resource_preference: Optional[str] = Field(default=None, description="资源偏好 (JSON list, e.g. ['mindmap','quiz'])")
    motivation: Optional[str] = Field(default=None, description="学习动机/目标强度")
    meta_learning_level: str = Field(default="medium", description="元学习能力: low/medium/high")
    emotion_tendency: Optional[str] = Field(default=None, description="情绪/挫折倾向")

    # Evidence & versioning
    raw_evidence: Optional[str] = Field(default=None, description="对话证据摘要")
    profile_source: Optional[str] = Field(default=None, description="画像来源: dialogue/quiz/behavior/manual")
    profile_version: int = Field(default=1, description="画像版本号")
    profile_confidence: float = Field(default=0.0, description="画像整体置信度")
    last_extracted_at: Optional[datetime] = Field(default=None, description="最后提取时间")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
