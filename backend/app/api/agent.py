"""Multi-agent tutor API."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.auth import get_current_user
from app.core.database import get_session
from app.models.course import Course
from app.models.user import User
from app.schemas.agent import TutorRequest, TutorResponse
from app.services.agent_graph import run_tutor_graph, MAX_TUTOR_TOP_K
from app.services.llm_provider import get_llm_provider

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post("/course/{course_id}/tutor", response_model=TutorResponse)
def api_tutor(
    course_id: int,
    body: TutorRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="course not found")

    result = run_tutor_graph(
        course_id=course_id,
        course_name=course.name,
        question=body.question,
        top_k=min(body.top_k, MAX_TUTOR_TOP_K),
        session=session,
        user=user,
    )

    llm = get_llm_provider()
    return TutorResponse(
        course_id=course_id,
        course_name=course.name or "",
        question=body.question,
        student_profile=result.get("student_profile", {}),
        retrieved_chunks=[
            {
                "chunk_id": c.get("chunk_id"),
                "course_id": c.get("course_id"),
                "file_id": c.get("file_id"),
                "content": c.get("content"),
                "source": c.get("source"),
                "page_number": c.get("page_number"),
            }
            for c in result.get("retrieved_chunks", [])
        ],
        draft_answer=result.get("draft_answer", ""),
        verified_answer=result.get("verified_answer", ""),
        citations=result.get("citations", []),
        verification=result.get("verification", {}),
        agent_trace=result.get("agent_trace", []),
        provider=llm.provider,
        model=llm.model,
    )
