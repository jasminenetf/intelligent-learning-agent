"""LLM + RAG Q&A API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.api.auth import get_current_user
from app.core.config import settings
from app.core.database import get_session
from app.models.user import User
from app.schemas.qa import (
    AskRequest,
    AskResponse,
    LLMStatusResponse,
    LLMTestRequest,
    LLMTestResponse,
)
from app.services.llm_provider import get_llm_provider
from app.services.qa_service import answer_course_question

router = APIRouter(tags=["llm-qa"])


def _require_teacher_or_admin(user: User):
    if user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="only teachers and admins can perform this action")


@router.get("/api/llm/status", response_model=LLMStatusResponse)
def api_llm_status(user: User = Depends(get_current_user)):
    _require_teacher_or_admin(user)
    provider = get_llm_provider()
    return LLMStatusResponse(
        provider=provider.provider,
        model=provider.model,
        is_mock=(provider.provider == "mock"),
        spark_configured=bool(settings.SPARK_API_PASSWORD or settings.SPARK_API_KEY),
        deepseek_configured=bool(settings.DEEPSEEK_API_KEY),
        embedding_provider=settings.EMBEDDING_PROVIDER,
        embedding_is_mock=(settings.EMBEDDING_PROVIDER == "hash_mock"),
    )


@router.post("/api/llm/test", response_model=LLMTestResponse)
def api_llm_test(body: LLMTestRequest, user: User = Depends(get_current_user)):
    _require_teacher_or_admin(user)
    provider = get_llm_provider()
    resp = provider.generate([{"role": "user", "content": body.message}])
    return LLMTestResponse(provider=resp.provider, model=resp.model, content=resp.content)


@router.post("/api/qa/courses/{course_id}/ask", response_model=AskResponse)
def api_qa_ask_post(
    course_id: int,
    body: AskRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    result = answer_course_question(course_id, body.question, body.top_k, session, user)
    if "error" in result:
        code = 404 if "not found" in result["error"] else 400
        raise HTTPException(status_code=code, detail=result["error"])
    return AskResponse(**result)


@router.get("/api/qa/courses/{course_id}/ask", response_model=AskResponse)
def api_qa_ask_get(
    course_id: int,
    q: str = Query(..., min_length=1),
    top_k: int = Query(default=5, ge=1),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    result = answer_course_question(course_id, q, top_k, session, user)
    if "error" in result:
        code = 404 if "not found" in result["error"] else 400
        raise HTTPException(status_code=code, detail=result["error"])
    return AskResponse(**result)
