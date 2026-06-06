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
from app.models.student_profile import StudentProfile
from app.models.student_profile_version import StudentProfileVersion
from app.models.student_profile_change_log import StudentProfileChangeLog
from app.models.user import User
from app.services.profile_service import get_or_create_profile, update_profile_from_behavior
from app.services.recommendation_service import build_wrong_book_review_actions
from app.services.study_plan_service import generate_study_plan

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
    profile = get_or_create_profile(uid, session)
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
        kp = a.knowledge_point or a.topic or "薄弱知识点"
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
                "review_actions": build_wrong_book_review_actions(kp, a.topic or "", profile),
            }
        )
    return {"ok": True, "items": items}


class ReviewPlanRequest(BaseModel):
    course_id: int = Field(..., ge=1)
    topic: str = Field(default="", min_length=0)
    knowledge_points: list[str] = Field(default_factory=list)


@router.post("/review-plan")
def create_review_plan(
    body: ReviewPlanRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Wrong-book → study plan → resource suggestions (learning closed loop)."""
    uid = int(user.id) if user.id else 0
    profile = get_or_create_profile(uid, session)
    topic = (body.topic or "").strip() or (body.knowledge_points[0] if body.knowledge_points else "错题复习")
    weak_points = [w for w in body.knowledge_points if w] or [topic]

    plan = generate_study_plan(
        course_id=body.course_id,
        topic=topic,
        profile=profile,
        session=session,
        top_k=8,
    )

    from app.services.recommendation_service import build_profile_next_actions, suggest_resources_from_question

    resource_suggestions = suggest_resources_from_question(topic, profile)
    next_actions = build_profile_next_actions(profile, weak_points, 0.0)

    try:
        update_profile_from_behavior(
            user,
            session,
            source="review_plan",
            text=topic,
            weak_points=weak_points[:5],
            preferred_content=["lecture_doc", "quiz", "mindmap"],
            learning_stage="review",
            confidence=0.15,
        )
    except Exception:
        pass

    return {
        "ok": True,
        "topic": topic,
        "weak_points": weak_points,
        "study_plan": plan,
        "next_actions": next_actions,
        "resource_suggestions": resource_suggestions,
    }


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
    try:
        update_profile_from_behavior(
            user,
            session,
            source="progress",
            text=body.next_recommendation or f"course={body.course_id}",
            weak_points=body.weak_points or [],
            learning_stage=(
                "foundation" if row.completed_rate < 0.35
                else ("consolidating" if row.completed_rate < 0.8 else "advanced")
            ),
            learning_pace="slow" if row.completed_rate < 0.3 else "moderate",
            confidence=0.1,
        )
    except Exception:
        pass
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
        try:
            update_profile_from_behavior(
                user,
                session,
                source="bookmark",
                text=body.title or body.resource_id,
                preferred_content=["mindmap", "lecture_doc"] if body.title else ["lecture_doc"],
                confidence=0.05,
            )
        except Exception:
            pass
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
    try:
        update_profile_from_behavior(
            user,
            session,
            source="bookmark",
            text=body.title or body.resource_id,
            preferred_content=["mindmap", "lecture_doc"] if body.title else ["lecture_doc"],
            confidence=0.08,
        )
    except Exception:
        pass
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
    try:
        if body.action in ("question_asked", "question_answered_with_citations", "question_answered_without_citations"):
            update_profile_from_behavior(
                user,
                session,
                source="audit",
                text=body.detail or body.action,
                learning_stage="practice",
                confidence=0.03,
            )
    except Exception:
        pass
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


@router.get("/profile-events")
def list_profile_events(
    limit: int = 20,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    uid = int(user.id) if user.id else 0
    profile = session.exec(select(StudentProfile).where(StudentProfile.user_id == uid)).first()
    if not profile:
        return {"ok": True, "versions": [], "changes": []}
    versions = session.exec(
        select(StudentProfileVersion)
        .where(StudentProfileVersion.profile_id == int(profile.id))
        .order_by(StudentProfileVersion.created_at.desc(), StudentProfileVersion.id.desc())
        .limit(limit)
    ).all()
    changes = session.exec(
        select(StudentProfileChangeLog)
        .where(StudentProfileChangeLog.profile_id == int(profile.id))
        .order_by(StudentProfileChangeLog.created_at.desc(), StudentProfileChangeLog.id.desc())
        .limit(limit)
    ).all()
    return {
        "ok": True,
        "versions": [
            {
                "id": v.id,
                "version": v.version,
                "trigger_source": v.trigger_source,
                "trigger_text": v.trigger_text,
                "confidence": v.confidence,
                "created_at": v.created_at,
                "snapshot_json": v.snapshot_json,
            }
            for v in versions
        ],
        "changes": [
            {
                "id": c.id,
                "field_name": c.field_name,
                "old_value": c.old_value,
                "new_value": c.new_value,
                "reason": c.reason,
                "source_type": c.source_type,
                "source_id": c.source_id,
                "created_at": c.created_at,
            }
            for c in changes
        ],
    }
