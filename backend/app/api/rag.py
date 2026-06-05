"""RAG API routes: build index, search, status."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.api.auth import get_current_user
from app.core.database import get_session
from app.models.user import User
from app.schemas.rag import (
    BuildIndexResponse,
    RagStatusResponse,
    SearchRequest,
    SearchResponse,
)
from app.services.rag_service import (
    build_course_index,
    get_rag_status,
    search_course,
)

router = APIRouter(prefix="/api/rag", tags=["rag"])


def _require_teacher_or_admin(user: User):
    if user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="only teachers and admins can perform this action")


@router.post("/courses/{course_id}/build", response_model=BuildIndexResponse)
def api_build_index(course_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    _require_teacher_or_admin(user)
    result = build_course_index(course_id, session)
    if "error" in result:
        code = 404 if "not found" in result["error"] else 400
        raise HTTPException(status_code=code, detail=result["error"])
    return BuildIndexResponse(**result)


@router.get("/courses/{course_id}/search", response_model=SearchResponse)
def api_search_get(
    course_id: int,
    q: str = Query(..., min_length=1),
    top_k: int = Query(default=5, ge=1, le=20),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    result = search_course(course_id, q, top_k, session)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return SearchResponse(**result)


@router.post("/courses/{course_id}/search", response_model=SearchResponse)
def api_search_post(
    course_id: int,
    body: SearchRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    result = search_course(course_id, body.query, body.top_k, session)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return SearchResponse(**result)


@router.get("/status", response_model=RagStatusResponse)
def api_rag_status(user: User = Depends(get_current_user), _session: Session = Depends(get_session)):
    _require_teacher_or_admin(user)
    return RagStatusResponse(**get_rag_status())
