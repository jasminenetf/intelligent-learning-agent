"""Quiz attempt service.

Handles quiz submission, wrong-point extraction and incremental
student-profile updates for the learning closed loop.
"""

from __future__ import annotations

import json
from typing import Any

from sqlmodel import Session, select

from app.models.quiz_attempt import QuizAttempt
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.services.mastery_service import update_knowledge_mastery
from app.services.profile_service import update_profile_from_behavior


def submit_quiz_attempt(*, body: Any, user: User, session: Session) -> dict[str, Any]:
    """Persist a quiz attempt and update profile weak points."""
    uid = int(user.id) if user.id else 0

    attempt = QuizAttempt(
        user_id=uid,
        course_id=body.course_id,
        topic=body.topic,
        question_text=body.question_text,
        selected_answer=body.selected_answer,
        correct_answer=body.correct_answer,
        is_correct=body.is_correct,
        knowledge_point=body.knowledge_point,
        explanation=body.explanation,
    )
    session.add(attempt)
    session.commit()
    session.refresh(attempt)

    updated_weak_points = _merge_wrong_knowledge_point(
        uid=uid,
        knowledge_point=body.knowledge_point,
        is_correct=body.is_correct,
        session=session,
    )

    mastery_row = None
    try:
        update_profile_from_behavior(
            user,
            session,
            source="quiz",
            text=body.question_text or body.topic or "quiz_attempt",
            weak_points=updated_weak_points or ([body.knowledge_point] if (not body.is_correct and body.knowledge_point) else []),
            preferred_content=["quiz", "lecture_doc"] if not body.is_correct else ["quiz"],
            cognitive_style="practice_oriented",
            learning_stage="review" if not body.is_correct else "practice",
            confidence=0.2 if not body.is_correct else 0.1,
        )
        mastery_row = update_knowledge_mastery(
            user_id=uid,
            course_id=body.course_id,
            knowledge_point=body.knowledge_point,
            is_correct=body.is_correct,
            session=session,
        )
    except Exception:
        pass

    return {
        "attempt_id": int(attempt.id) if attempt.id else 0,
        "is_correct": body.is_correct,
        "updated_weak_points": updated_weak_points,
        "mastery": {
            "knowledge_point": mastery_row.knowledge_point if mastery_row else None,
            "mastery_score": mastery_row.mastery_score if mastery_row else None,
            "recommended_action": mastery_row.recommended_action if mastery_row else None,
        },
        "message": "作答已记录，学习画像已更新",
    }


def _merge_wrong_knowledge_point(*, uid: int, knowledge_point: str, is_correct: bool, session: Session) -> list[str]:
    if is_correct or not knowledge_point:
        return []

    profile = session.exec(
        select(StudentProfile).where(StudentProfile.user_id == uid)
    ).first()
    if not profile:
        return []

    existing: list[str] = []
    if profile.weak_points:
        try:
            parsed = json.loads(profile.weak_points)
            existing = [str(x) for x in parsed] if isinstance(parsed, list) else [profile.weak_points]
        except Exception:
            existing = [profile.weak_points]

    if knowledge_point not in existing:
        existing.append(knowledge_point)
        profile.weak_points = json.dumps(existing, ensure_ascii=False)
        session.add(profile)
        session.commit()

    return existing
