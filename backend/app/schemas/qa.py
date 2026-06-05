"""RAG Q&A schemas."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)

    @field_validator("top_k")
    @classmethod
    def clamp_top_k(cls, v: int) -> int:
        return min(v, 10)


class Citation(BaseModel):
    chunk_id: Optional[int] = None
    source: Optional[str] = None
    page_number: Optional[int] = None
    score: Optional[float] = None


class RetrievedChunk(BaseModel):
    chunk_id: Optional[int] = None
    course_id: Optional[int] = None
    file_id: Optional[int] = None
    chunk_index: Optional[int] = None
    content: Optional[str] = None
    source: Optional[str] = None
    page_number: Optional[int] = None


class AskResponse(BaseModel):
    course_id: int
    course_name: str
    question: str
    answer: str
    provider: str
    model: str
    citations: list[Citation] = []
    retrieved_chunks: list[RetrievedChunk] = []


class LLMTestRequest(BaseModel):
    message: str = Field(..., min_length=1)


class LLMTestResponse(BaseModel):
    provider: str
    model: str
    content: str


class LLMStatusResponse(BaseModel):
    provider: str
    model: str
    is_mock: bool
    spark_configured: bool
    deepseek_configured: bool
    embedding_provider: str
    embedding_is_mock: bool
