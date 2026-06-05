"""RAG request/response schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class BuildIndexResponse(BaseModel):
    course_id: int
    indexed_chunks: int
    collection: str
    provider: str


class SearchResultItem(BaseModel):
    chunk_id: int
    course_id: int
    file_id: int
    chunk_index: int
    content: str
    source: str
    page_number: Optional[int] = None
    score: float


class SearchResponse(BaseModel):
    course_id: Optional[int]
    query: str
    results: list[SearchResultItem]


class RagStatusResponse(BaseModel):
    collection: str
    persist_dir: str
    embedding_provider: str
    embedding_dim: int
