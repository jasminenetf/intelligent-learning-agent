"""Learning report service.

Builds quiz-based learning reports and connects weak points,
profile state and resource recommendations into one closed loop.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlmodel import Session, select

from app.models.quiz_attempt import QuizAttempt
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.services.mastery_service import list_user_mastery, mastery_summary
from app.services.profile_service import update_profile_from_behavior
from app.services.recommendation_service import build_profile_next_actions


def build_learning_report(
    *,
    user: User,
    session: Session,
    course_id: Optional[int] = None,
    topic: Optional[str] = None,
) -> dict[str, Any]:
    """Build a learning report from quiz attempts and profile state."""
    uid = int(user.id) if user.id else 0

    stmt = select(QuizAttempt).where(QuizAttempt.user_id == uid)
    if course_id is not None:
        stmt = stmt.where(QuizAttempt.course_id == course_id)
    if topic:
        stmt = stmt.where(QuizAttempt.topic == topic)

    attempts = session.exec(stmt).all()
    profile = session.exec(
        select(StudentProfile).where(StudentProfile.user_id == uid)
    ).first()
    mastery_items = list_user_mastery(user_id=uid, course_id=course_id or (attempts[0].course_id if attempts else 0), session=session) if (course_id or attempts) else []
    mastery_overview = mastery_summary(mastery_items)

    total = len(attempts)
    if total == 0:
        next_actions = build_profile_next_actions(profile, [], 0.0) if profile else []
        return {
            "total_attempts": 0,
            "correct_count": 0,
            "accuracy": 0.0,
            "weak_points": [],
            "recommended_resources": [],
            "next_actions": next_actions,
            "profile_summary": _profile_summary(profile),
            "mastery_overview": mastery_overview,
            "mastery_items": [],
            "profile_updated": False,
        }

    correct = sum(1 for a in attempts if a.is_correct)
    accuracy = round(correct / total, 2) if total > 0 else 0.0
    weak_points = _collect_weak_points(attempts)
    recommended = _recommend_resources(weak_points)
    next_actions = build_profile_next_actions(profile, weak_points, accuracy)

    try:
        update_profile_from_behavior(
            user,
            session,
            source="report",
            text=topic or f"course={course_id or 'all'}",
            weak_points=weak_points[:5],
            preferred_content=[r.get("type", "quiz") for r in recommended[:3] if isinstance(r, dict)],
            cognitive_style="logical" if accuracy >= 0.8 else "practice_oriented",
            learning_stage="review" if accuracy < 0.5 else ("practice" if accuracy < 0.8 else "advanced"),
            learning_pace="slow" if accuracy < 0.4 else "moderate",
            confidence=0.12,
        )
    except Exception:
        pass

    return {
        "total_attempts": total,
        "correct_count": correct,
        "accuracy": accuracy,
        "weak_points": weak_points,
        "recommended_resources": recommended,
        "next_actions": next_actions,
        "profile_summary": _profile_summary(profile),
        "mastery_overview": mastery_overview,
        "mastery_items": [
            {
                "knowledge_point": item.knowledge_point,
                "mastery_score": item.mastery_score,
                "attempt_count": item.attempt_count,
                "correct_count": item.correct_count,
                "wrong_count": item.wrong_count,
                "recommended_action": item.recommended_action,
            }
            for item in mastery_items
        ],
        "profile_updated": bool(profile and profile.weak_points and profile.weak_points != "[]"),
    }


def _collect_weak_points(attempts: list[QuizAttempt]) -> list[str]:
    wp_counts: dict[str, int] = {}
    for attempt in attempts:
        if not attempt.is_correct and attempt.knowledge_point:
            wp_counts[attempt.knowledge_point] = wp_counts.get(attempt.knowledge_point, 0) + 1
    return sorted(wp_counts.keys(), key=lambda k: -wp_counts[k])


def _recommend_resources(weak_points: list[str]) -> list[dict[str, str]]:
    resource_map = {
        "正则化": [
            {"type": "mindmap", "title": "正则化知识结构图"},
            {"type": "quiz", "title": "正则化专项练习"},
        ],
        "过拟合": [
            {"type": "lecture_doc", "title": "过拟合详解讲义"},
            {"type": "quiz", "title": "过拟合专项练习"},
        ],
        "欠拟合": [
            {"type": "study_plan", "title": "欠拟合学习路径"},
            {"type": "quiz", "title": "欠拟合专项练习"},
        ],
        "过拟合与正则化": [
            {"type": "mindmap", "title": "过拟合与正则化知识结构图"},
            {"type": "quiz", "title": "巩固练习"},
        ],
    }
    recommended: list[dict[str, str]] = []
    seen: set[str] = set()
    for weak_point in weak_points:
        for resource in resource_map.get(weak_point, resource_map.get("过拟合与正则化", [])):
            if resource["title"] not in seen:
                recommended.append(resource)
                seen.add(resource["title"])
    if recommended:
        return recommended
    return [
        {"type": "mindmap", "title": "知识结构图"},
        {"type": "study_plan", "title": "个性化学习路径"},
    ]


def _profile_summary(profile: StudentProfile | None) -> dict[str, Any]:
    return {
        "learning_goal": getattr(profile, "learning_goal", None) if profile else None,
        "knowledge_level": getattr(profile, "knowledge_level", None) if profile else None,
    }
