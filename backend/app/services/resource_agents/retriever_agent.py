"""Retriever agent: gather course evidence for generation."""

from typing import Any

from sqlmodel import Session

from app.services.rag_service import search_course


def retrieve(
    course_id: int,
    topic: str,
    plan_result: dict,
    student_profile: Any,
    session: Session,
    top_k: int = 5,
) -> dict:
    search_result = search_course(course_id, topic, top_k=top_k, session=session)
    hits = search_result.get("results") if isinstance(search_result, dict) else search_result
    chunks = []
    for h in hits or []:
        chunks.append({
            "chunk_id": h.get("chunk_id"),
            "source": h.get("source") or h.get("filename") or "course",
            "content": (h.get("content") or h.get("text") or "")[:500],
            "score": h.get("score"),
        })
    return {
        "topic": topic,
        "chunks": chunks,
        "chunk_count": len(chunks),
        "evidence_summary": f"检索到 {len(chunks)} 条课程片段" if chunks else "未检索到课程片段，将使用模板降级",
    }
