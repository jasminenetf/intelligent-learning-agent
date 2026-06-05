"""RAG service: build indices and search across course chunks."""

import logging
from typing import Optional

from sqlmodel import Session, select

from app.core.config import settings
from app.models.course import Course
from app.models.knowledge_chunk import KnowledgeChunk
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

_embedding_service: Optional[EmbeddingService] = None
_vector_store: Optional[VectorStoreService] = None

MAX_TOP_K = 20


def _get_services() -> tuple[EmbeddingService, VectorStoreService]:
    global _embedding_service, _vector_store
    if _embedding_service is None:
        _embedding_service = EmbeddingService(
            provider=settings.EMBEDDING_PROVIDER,
            dim=settings.EMBEDDING_DIM,
        )
    if _vector_store is None:
        _vector_store = VectorStoreService(
            persist_dir=settings.CHROMA_PERSIST_DIR,
            collection_name=settings.CHROMA_COLLECTION_NAME,
            embedding_service=_embedding_service,
        )
    return _embedding_service, _vector_store


def build_course_index(course_id: int, session: Session) -> dict:
    """Read knowledge_chunks from SQLite and upsert into ChromaDB."""
    course = session.get(Course, course_id)
    if not course:
        return {"error": "course not found", "course_id": course_id}

    chunks = session.exec(
        select(KnowledgeChunk).where(KnowledgeChunk.course_id == course_id)
    ).all()

    if not chunks:
        return {"error": "no chunks found for this course", "course_id": course_id}

    _, vs = _get_services()
    chunk_dicts = [
        {
            "chunk_id": c.id,
            "content": c.content,
            "course_id": c.course_id,
            "file_id": c.file_id,
            "chunk_index": c.chunk_index,
            "source": c.source,
            "page_number": c.page_number,
        }
        for c in chunks
    ]
    result = vs.upsert_chunks(chunk_dicts)
    return {
        "course_id": course_id,
        "indexed_chunks": result["indexed"],
        "collection": settings.CHROMA_COLLECTION_NAME,
        "provider": settings.EMBEDDING_PROVIDER,
    }


def search_course(course_id: int, query: str, top_k: int, session: Session) -> dict:
    """Search ChromaDB for chunks matching query, filtered by course_id."""
    course = session.get(Course, course_id)
    if not course:
        return {"error": "course not found", "course_id": course_id}

    top_k = min(top_k, MAX_TOP_K)
    _, vs = _get_services()
    results = vs.search(query=query, course_id=course_id, top_k=top_k)
    return {
        "course_id": course_id,
        "query": query,
        "results": results,
    }


def search_all_courses(query: str, top_k: int, session: Session) -> dict:
    """Search across all courses (no course_id filter)."""
    top_k = min(top_k, MAX_TOP_K)
    _, vs = _get_services()
    results = vs.search(query=query, course_id=None, top_k=top_k)
    return {
        "course_id": None,
        "query": query,
        "results": results,
    }


def get_rag_status() -> dict:
    """Return RAG component status."""
    _, vs = _get_services()
    return {
        "collection": settings.CHROMA_COLLECTION_NAME,
        "persist_dir": settings.CHROMA_PERSIST_DIR,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "embedding_dim": settings.EMBEDDING_DIM,
        "vector_count": vs.count(),
    }
