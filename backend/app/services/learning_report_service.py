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
        "函数极限": [
            {"type": "lecture_doc", "title": "函数极限定义讲义"},
            {"type": "mindmap", "title": "函数极限知识结构图"},
        ],
        "左右极限": [
            {"type": "mindmap", "title": "左右极限判断清单"},
            {"type": "quiz", "title": "左右极限专项练习"},
        ],
        "无穷小": [
            {"type": "lecture_doc", "title": "无穷小与等价无穷小讲义"},
            {"type": "quiz", "title": "无穷小计算练习"},
        ],
        "连续": [
            {"type": "mindmap", "title": "连续性条件知识结构图"},
            {"type": "quiz", "title": "连续性判断练习"},
        ],
        "导数": [
            {"type": "lecture_doc", "title": "导数定义与几何意义讲义"},
            {"type": "quiz", "title": "导数基础专项练习"},
        ],
        "积分": [
            {"type": "lecture_doc", "title": "积分概念与基本方法讲义"},
            {"type": "study_plan", "title": "积分方法学习路径"},
        ],
    }
    recommended: list[dict[str, str]] = []
    seen: set[str] = set()
    for weak_point in weak_points:
        matched = []
        for key, resources in resource_map.items():
            if key in weak_point:
                matched = resources
                break
        for resource in matched or resource_map["函数极限"]:
            if resource["title"] not in seen:
                recommended.append(resource)
                seen.add(resource["title"])
    if recommended:
        return recommended
    return [
        {"type": "mindmap", "title": "函数极限知识结构图"},
        {"type": "study_plan", "title": "高等数学上册个性化学习路径"},
    ]


def _profile_summary(profile: StudentProfile | None) -> dict[str, Any]:
    return {
        "learning_goal": getattr(profile, "learning_goal", None) if profile else None,
        "knowledge_level": getattr(profile, "knowledge_level", None) if profile else None,
    }
