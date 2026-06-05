"""Multi-agent tutor schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class TutorRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class StudentProfile(BaseModel):
    knowledge_level: str = "intermediate"
    cognitive_style: str = "conceptual"
    needs_examples: bool = False
    needs_step_by_step: bool = False
    detected_weakness: str = ""


class AgentTraceItem(BaseModel):
    agent: str
    status: str
    intent: Optional[str] = None
    knowledge_level: Optional[str] = None
    cognitive_style: Optional[str] = None
    chunks_found: Optional[int] = None
    answer_len: Optional[int] = None
    error: Optional[str] = None
    reason: Optional[str] = None


class Citation(BaseModel):
    chunk_id: Optional[int] = None
    source: Optional[str] = None
    page_number: Optional[int] = None
    score: Optional[float] = None


class RetrievedChunk(BaseModel):
    chunk_id: Optional[int] = None
    course_id: Optional[int] = None
    file_id: Optional[int] = None
    content: Optional[str] = None
    source: Optional[str] = None
    page_number: Optional[int] = None


class VerificationResult(BaseModel):
    verdict: str
    reasons: list[str] = []


class TutorResponse(BaseModel):
    course_id: int
    course_name: str
    question: str
    student_profile: StudentProfile = StudentProfile()
    retrieved_chunks: list[RetrievedChunk] = []
    draft_answer: str = ""
    verified_answer: str = ""
    citations: list[Citation] = []
    verification: VerificationResult = VerificationResult(verdict="unknown")
    agent_trace: list[AgentTraceItem] = []
    provider: str = "mock"
    model: str = "mock"
