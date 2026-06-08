"""
Application workspace API.

Prefix: /api/app

Provides bootstrap, dashboard, ask, generate and related
workspace endpoints for the learning product UI.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.api.auth import get_current_user, get_current_user_optional
from app.core.database import get_session
from app.models.user import User
from app.api.workspace import (
    ok as _ok,
    err as _err,
    dashboard_payload,
    bootstrap_payload,
    llm_configured,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/app", tags=["app"])

# ── Error codes ────────────────────────────────────────────────────────
ERR_NOT_CONFIGURED = "NOT_CONFIGURED"
ERR_NOT_AUTHENTICATED = "NOT_AUTHENTICATED"
ERR_COURSE_NOT_FOUND = "COURSE_NOT_FOUND"
ERR_NO_KNOWLEDGE_BASE = "NO_KNOWLEDGE_BASE"
ERR_LLM_FAILED = "LLM_FAILED"
ERR_RESOURCE_FAILED = "RESOURCE_FAILED"

# Helpers and workspace routes moved to `app/api/workspace.py`.


# ═══════════════════════════════════════════════════════════════════════
# GET /api/app/bootstrap — app init payload (guest or authenticated)
# ═══════════════════════════════════════════════════════════════════════

@router.get("/bootstrap")
def api_app_bootstrap(
    user: Optional[User] = Depends(get_current_user_optional),
    session: Session = Depends(get_session),
):
    return bootstrap_payload(user, session)


# ═══════════════════════════════════════════════════════════════════════
# GET /api/app/dashboard — course workspace summary
# ═══════════════════════════════════════════════════════════════════════

@router.get("/dashboard")
def api_app_dashboard(
    course_id: Optional[int] = None,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return dashboard_payload(course_id, user, session)


# ═══════════════════════════════════════════════════════════════════════
# POST /api/app/ask
# ═══════════════════════════════════════════════════════════════════════

from pydantic import BaseModel, Field

class AppAskRequest(BaseModel):
    course_id: int = Field(default=2)
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=8, ge=1, le=20)
    session_id: Optional[int] = Field(default=None, description="学习会话 ID，用于历史持久化")


@router.post("/ask")
def api_app_ask(
    body: AppAskRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Unified Q&A — multi-agent graph pipeline with agent traces."""
    from app.services.app_ask_service import answer_workspace_question

    return answer_workspace_question(body=body, user=user, session=session)


# ═══════════════════════════════════════════════════════════════════════
# POST /api/app/ask/stream — SSE streaming RAG answer
# ═══════════════════════════════════════════════════════════════════════

@router.post("/ask/stream")
async def api_app_ask_stream(
    body: AppAskRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Stream RAG answer via Server-Sent Events (commercial UX)."""
    from app.services.app_stream_service import stream_workspace_question

    return stream_workspace_question(body=body, user=user, session=session)


# ═══════════════════════════════════════════════════════════════════════
# POST /api/app/generate
# ═══════════════════════════════════════════════════════════════════════

class AppGenerateRequest(BaseModel):
    course_id: int = Field(default=2)
    resource_type: str = Field(..., description="mindmap, lecture_doc, quiz, ppt, study_plan")
    topic: str = Field(default="导数与极限入门", min_length=1)


@router.post("/generate")
def api_app_generate(
    body: AppGenerateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Unified resource generation — wraps resource generator + study plan."""
    try:
        from app.services.app_resource_service import generate_workspace_resource

        return _ok(generate_workspace_resource(body=body, user=user, session=session))
    except HTTPException:
        raise
    except ValueError as e:
        msg = str(e)
        if "course not found" in msg:
            raise HTTPException(status_code=404, detail=ERR_COURSE_NOT_FOUND)
        if "no relevant" in msg:
            raise HTTPException(status_code=400, detail=ERR_NO_KNOWLEDGE_BASE)
        raise HTTPException(status_code=500, detail=f"{ERR_RESOURCE_FAILED}: {msg}")
    except Exception as e:
        logger.exception("Resource generation failed")
        raise HTTPException(status_code=500, detail=f"{ERR_RESOURCE_FAILED}: {e}")


# ═══════════════════════════════════════════════════════════════════════
# POST /api/app/run-demo
# ═══════════════════════════════════════════════════════════════════════

@router.post("/run-demo")
def api_run_demo():
    """Deprecated demo pipeline endpoint."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "code": "DEPRECATED",
            "message": "run_demo is deprecated. Use the standard workspace endpoints instead.",
        },
    )


# ═══════════════════════════════════════════════════════════════════════
# POST /api/app/quiz/submit
# ═══════════════════════════════════════════════════════════════════════

from pydantic import BaseModel as PydanticBaseModel


class QuizSubmitRequest(PydanticBaseModel):
    course_id: int = 0
    topic: str = ""
    question_text: str = ""
    selected_answer: str = ""
    correct_answer: str = ""
    is_correct: bool = False
    knowledge_point: str = ""
    explanation: str = ""


@router.post("/quiz/submit")
def api_quiz_submit(
    body: QuizSubmitRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Record a quiz answer and update student profile weak_points."""
    from app.services.quiz_service import submit_quiz_attempt

    return _ok(submit_quiz_attempt(body=body, user=user, session=session))


# ═══════════════════════════════════════════════════════════════════════
# GET /api/app/learning-report
# ═══════════════════════════════════════════════════════════════════════

@router.get("/learning-report")
def api_learning_report(
    course_id: Optional[int] = None,
    topic: Optional[str] = None,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Generate a learning evaluation report from quiz attempts."""
    from app.services.learning_report_service import build_learning_report

    return _ok(build_learning_report(user=user, session=session, course_id=course_id, topic=topic))
