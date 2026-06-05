"""Learning analytics, audit, and bookmark APIs."""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.api.auth import get_current_user
from app.core.database import get_session
from app.models.learning_analytics import AuditLog, LearningProgress, ResourceBookmark
from app.models.quiz_attempt import QuizAttempt
from app.models.user import User

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class BookmarkCreateRequest(BaseModel):
    resource_id: str = Field(..., min_length=1)
    title: str = Field(default="")


class ProgressUpsertRequest(BaseModel):
    course_id: int
    completed_lessons: int = Field(default=0, ge=0)
    total_lessons: int = Field(default=0, ge=0)
    weak_points: Optional[list[str]] = None
    next_recommendation: Optional[str] = None


class AuditCreateRequest(BaseModel):
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    detail: Optional[str] = None


@router.get("/dashboard")
def get_dashboard_stats(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    uid = int(user.id) if user.id else 0
    attempts = session.exec(select(QuizAttempt).where(QuizAttempt.user_id == uid)).all()
    correct = sum(1 for a in attempts if a.is_correct)
    total = len(attempts)
    bookmarks = session.exec(select(ResourceBookmark).where(ResourceBookmark.user_id == uid)).all()
    progress_rows = session.exec(select(LearningProgress).where(LearningProgress.user_id == uid)).all()
    return {
        "ok": True,
        "stats": {
            "quiz_total": total,
            "quiz_correct": correct,
            "quiz_accuracy": round(correct / total, 2) if total else 0.0,
            "bookmark_count": len(bookmarks),
            "course_count": len(progress_rows),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    }


@router.get("/wrong-book")
def get_wrong_book(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    uid = int(user.id) if user.id else 0
    attempts = session.exec(select(QuizAttempt).where(QuizAttempt.user_id == uid)).all()
    items = []
    seen = set()
    for a in attempts:
        if a.is_correct:
            continue
        key = (a.course_id, a.knowledge_point, a.question_text)
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {
                "id": a.id,
                "course_id": a.course_id,
                "topic": a.topic,
                "question_text": a.question_text,
                "selected_answer": a.selected_answer,
                "correct_answer": a.correct_answer,
                "knowledge_point": a.knowledge_point,
                "explanation": a.explanation,
                "created_at": a.created_at,
            }
        )
    return {"ok": True, "items": items}


@router.get("/progress")
def list_progress(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    uid = int(user.id) if user.id else 0
    rows = session.exec(select(LearningProgress).where(LearningProgress.user_id == uid)).all()
    return {
        "ok": True,
        "items": [
            {
                "id": r.id,
                "course_id": r.course_id,
                "completed_lessons": r.completed_lessons,
                "total_lessons": r.total_lessons,
                "completed_rate": r.completed_rate,
                "weak_points": r.weak_points,
                "next_recommendation": r.next_recommendation,
                "updated_at": r.updated_at,
            }
            for r in rows
        ],
    }


@router.post("/progress")
def upsert_progress(
    body: ProgressUpsertRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    uid = int(user.id) if user.id else 0
    row = session.exec(
        select(LearningProgress).where(
            LearningProgress.user_id == uid,
            LearningProgress.course_id == body.course_id,
        )
    ).first()
    weak_points = None
    if body.weak_points is not None:
        import json
        weak_points = json.dumps(body.weak_points, ensure_ascii=False)
    if not row:
        row = LearningProgress(
            user_id=uid,
            course_id=body.course_id,
            completed_lessons=body.completed_lessons,
            total_lessons=body.total_lessons,
            completed_rate=(body.completed_lessons / body.total_lessons) if body.total_lessons else 0.0,
            weak_points=weak_points,
            next_recommendation=body.next_recommendation,
        )
    else:
        row.completed_lessons = body.completed_lessons
        row.total_lessons = body.total_lessons
        row.completed_rate = (body.completed_lessons / body.total_lessons) if body.total_lessons else 0.0
        row.weak_points = weak_points if weak_points is not None else row.weak_points
        row.next_recommendation = body.next_recommendation
        row.updated_at = datetime.now(timezone.utc)
    session.add(row)
    session.add(AuditLog(user_id=uid, action="progress_upsert", target_type="course", target_id=str(body.course_id), detail=f"completed={body.completed_lessons}, total={body.total_lessons}"))
    session.commit()
    session.refresh(row)
    return {"ok": True, "progress": row.model_dump(mode="json")}


@router.get("/bookmarks")
def list_bookmarks(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    uid = int(user.id) if user.id else 0
    rows = session.exec(select(ResourceBookmark).where(ResourceBookmark.user_id == uid)).all()
    return {
        "ok": True,
        "items": [
            {
                "id": r.id,
                "resource_id": r.resource_id,
                "title": r.title,
                "shared_token": r.shared_token,
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }


@router.post("/bookmarks")
def create_bookmark(
    body: BookmarkCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    uid = int(user.id) if user.id else 0
    existing = session.exec(
        select(ResourceBookmark).where(
            ResourceBookmark.user_id == uid,
            ResourceBookmark.resource_id == body.resource_id,
        )
    ).first()
    if existing:
        return {"ok": True, "bookmark": existing.model_dump(mode="json"), "created": False}
    row = ResourceBookmark(
        user_id=uid,
        resource_id=body.resource_id,
        title=body.title,
        shared_token=uuid4().hex[:12],
    )
    session.add(row)
    session.add(AuditLog(user_id=uid, action="bookmark_create", target_type="resource", target_id=body.resource_id, detail=body.title or body.resource_id))
    session.commit()
    session.refresh(row)
    return {"ok": True, "bookmark": row.model_dump(mode="json"), "created": True}


@router.post("/audit")
def create_audit(
    body: AuditCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    uid = int(user.id) if user.id else None
    row = AuditLog(
        user_id=uid,
        action=body.action,
        target_type=body.target_type,
        target_id=body.target_id,
        detail=body.detail,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return {"ok": True, "audit": row.model_dump(mode="json")}


@router.get("/audit")
def list_audit_logs(
    limit: int = 20,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    uid = int(user.id) if user.id else 0
    rows = session.exec(
        select(AuditLog)
        .where(AuditLog.user_id == uid)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
    ).all()
    return {
        "ok": True,
        "items": [
            {
                "id": r.id,
                "action": r.action,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "detail": r.detail,
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }
