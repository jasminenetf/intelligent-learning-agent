"""Knowledge mastery service for per-point learning progress."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from app.models.knowledge_mastery import KnowledgeMastery


def update_knowledge_mastery(*, user_id: int, course_id: int, knowledge_point: str, is_correct: bool, session: Session) -> KnowledgeMastery:
    """Upsert and update mastery for one knowledge point."""
    kp = (knowledge_point or '').strip() or '未命名知识点'
    row = session.exec(
        select(KnowledgeMastery).where(
            KnowledgeMastery.user_id == user_id,
            KnowledgeMastery.course_id == course_id,
            KnowledgeMastery.knowledge_point == kp,
        )
    ).first()

    if not row:
        row = KnowledgeMastery(
            user_id=user_id,
            course_id=course_id,
            knowledge_point=kp,
            mastery_score=0.55 if is_correct else 0.35,
            attempt_count=1,
            correct_count=1 if is_correct else 0,
            wrong_count=0 if is_correct else 1,
            last_practiced_at=datetime.now(timezone.utc),
            recommended_action=_recommended_action(0.55 if is_correct else 0.35),
        )
    else:
        row.attempt_count += 1
        if is_correct:
            row.correct_count += 1
            row.mastery_score = min(1.0, round(row.mastery_score + 0.08, 2))
        else:
            row.wrong_count += 1
            row.mastery_score = max(0.0, round(row.mastery_score - 0.12, 2))
        row.last_practiced_at = datetime.now(timezone.utc)
        row.recommended_action = _recommended_action(row.mastery_score)
        row.updated_at = datetime.now(timezone.utc)

    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_user_mastery(*, user_id: int, course_id: int, session: Session) -> list[KnowledgeMastery]:
    return session.exec(
        select(KnowledgeMastery).where(
            KnowledgeMastery.user_id == user_id,
            KnowledgeMastery.course_id == course_id,
        )
    ).all()


def mastery_summary(items: list[KnowledgeMastery]) -> dict[str, object]:
    if not items:
        return {"avg_mastery": 0.0, "strong_points": [], "weak_points": []}
    avg = round(sum(i.mastery_score for i in items) / len(items), 2)
    strong = [i.knowledge_point for i in items if i.mastery_score >= 0.75]
    weak = [i.knowledge_point for i in items if i.mastery_score < 0.5]
    return {"avg_mastery": avg, "strong_points": strong[:5], "weak_points": weak[:5]}


def _recommended_action(score: float) -> str:
    if score < 0.4:
        return "先看讲义并完成基础练习"
    if score < 0.7:
        return "继续练习并复盘错题"
    return "可进入进阶拓展"
