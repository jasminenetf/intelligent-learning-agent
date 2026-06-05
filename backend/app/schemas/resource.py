"""Resource generation schemas for unified resource layer.

Resource types: mindmap, lecture_doc, quiz.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ResourceType(str, Enum):
    MINDMAP = "mindmap"
    LECTURE_DOC = "lecture_doc"
    QUIZ = "quiz"
    PPT = "ppt"
    STUDY_PLAN = "study_plan"


# --- MindMap schemas ---

class MindMapNode(BaseModel):
    id: str = Field(..., min_length=1, description="Unique node identifier")
    label: str = Field(..., min_length=1, max_length=40, description="Node label (max 40 chars)")
    children: list["MindMapNode"] = Field(default_factory=list, description="Child nodes")

    @field_validator("label")
    @classmethod
    def strip_label(cls, v: str) -> str:
        return v.strip()


class MindMapJSON(BaseModel):
    title: str = Field(..., min_length=1, description="Mind map root title")
    nodes: list[MindMapNode] = Field(..., min_length=1, description="Root-level nodes (min 1)")


# --- Lecture Doc schemas ---

class LectureSection(BaseModel):
    heading: str = Field(..., min_length=1, description="Section heading")
    content: str = Field(..., min_length=1, description="Section body text")


class LectureDocJSON(BaseModel):
    title: str = Field(..., min_length=1, description="Lecture document title")
    difficulty: str = Field(default="intermediate", description="Target difficulty: beginner/intermediate/advanced")
    sections: list[LectureSection] = Field(..., min_length=1, description="Content sections (min 1)")


# --- Quiz schemas ---

class QuizItem(BaseModel):
    question: str = Field(..., min_length=1, description="Quiz question text")
    options: list[str] = Field(..., min_length=2, description="Answer options (min 2)")
    answer: int = Field(..., ge=0, description="Correct option index (0-based)")
    explanation: str = Field(..., min_length=1, description="Explanation of the correct answer")

    @field_validator("answer")
    @classmethod
    def answer_in_range(cls, v: int, info) -> int:
        # Options not yet validated at field level, validate in model_validator
        return v

    @field_validator("options")
    @classmethod
    def strip_options(cls, v: list[str]) -> list[str]:
        return [o.strip() for o in v]


class QuizJSON(BaseModel):
    title: str = Field(..., min_length=1, description="Quiz title")
    items: list[QuizItem] = Field(..., min_length=1, description="Quiz items (min 1)")


# --- Unified resource pack ---

class StudentProfile(BaseModel):
    knowledge_level: str = Field(default="intermediate", description="beginner/intermediate/advanced")
    cognitive_style: str = Field(default="conceptual", description="conceptual/logical/practice_oriented")


class ResourcePackRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="Topic or question to generate resources for")
    resource_types: list[ResourceType] = Field(..., min_length=1, description="Resource types to generate")
    student_profile: StudentProfile = Field(default_factory=StudentProfile)
    top_k: int = Field(default=5, ge=1, le=20)


class ResourceItem(BaseModel):
    type: ResourceType
    title: str
    # For mindmap
    mermaid: Optional[str] = None
    raw_json: Optional[dict] = None
    # For lecture_doc
    content: Optional[str] = None
    # For quiz
    items: Optional[list[dict]] = None
    # For ppt
    resource_id: Optional[str] = None
    filename: Optional[str] = None
    download_url: Optional[str] = None
    slide_count: Optional[int] = None
    # For study_plan
    study_plan: Optional[dict] = None
    # Metadata
    generated_by: str = "fallback_template"
    used_rag: bool = True
    used_profile: bool = False
    fallback_used: bool = True
    context_chunks: int = 0


class Citation(BaseModel):
    chunk_id: Optional[int] = None
    source: Optional[str] = None
    page_number: Optional[int] = None
    score: Optional[float] = None


class ResourcePackResponse(BaseModel):
    course_id: int
    course_name: str
    topic: str
    resources: list[ResourceItem] = []
    citations: list[Citation] = []
    provider: str = "mock"
    model: str = "mock"
