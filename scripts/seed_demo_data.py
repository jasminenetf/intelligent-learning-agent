#!/usr/bin/env python3
"""Seed repeatable demo data for the intelligent learning agent.

This script creates a demo course with usable RAG chunks, a student profile,
quiz attempts, mastery records, progress rows, bookmarks, and audit logs.
It is idempotent: re-running updates existing records instead of duplicating the
core user/course/profile/progress/mastery rows.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sqlmodel import Session, select  # noqa: E402

from app.core.database import create_db_and_tables, engine  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.course import Course  # noqa: E402
from app.models.course_file import CourseFile  # noqa: E402
from app.models.knowledge_chunk import KnowledgeChunk  # noqa: E402
from app.models.knowledge_mastery import KnowledgeMastery  # noqa: E402
from app.models.learning_analytics import AuditLog, LearningProgress, ResourceBookmark  # noqa: E402
from app.models.quiz_attempt import QuizAttempt  # noqa: E402
from app.models.student_profile import StudentProfile  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.rag_service import build_course_index  # noqa: E402

SEED_FILE = ROOT / "seed" / "demo_course_ai_intro.json"


def _load_seed() -> dict:
    return json.loads(SEED_FILE.read_text(encoding="utf-8"))


def _get_or_create_user(session: Session, data: dict, role: str) -> User:
    user = session.exec(select(User).where(User.username == data["username"])).first()
    if not user:
        user = User(
            username=data["username"],
            email=data.get("email"),
            hashed_password=get_password_hash(data["password"]),
            role=role,
            is_active=True,
        )
    else:
        user.email = data.get("email") or user.email
        user.role = role
        user.is_active = True
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _get_or_create_course(session: Session, teacher: User, data: dict) -> Course:
    course = session.exec(select(Course).where(Course.name == data["name"])).first()
    if not course:
        course = Course(name=data["name"], description=data.get("description"), teacher_id=int(teacher.id or 0))
    else:
        course.description = data.get("description") or course.description
        course.teacher_id = int(teacher.id or course.teacher_id)
    session.add(course)
    session.commit()
    session.refresh(course)
    return course


def _seed_course_chunks(session: Session, course: Course, teacher: User, chunks: list[dict]) -> int:
    source_name = "demo_course_ai_intro.json"
    file_row = session.exec(
        select(CourseFile).where(
            CourseFile.course_id == course.id,
            CourseFile.original_filename == source_name,
        )
    ).first()
    if not file_row:
        file_row = CourseFile(
            course_id=int(course.id or 0),
            uploader_id=int(teacher.id or 0),
            original_filename=source_name,
            stored_path=str(SEED_FILE),
            content_type="application/json",
            file_ext=".json",
            file_size=SEED_FILE.stat().st_size,
            status="processed",
        )
    else:
        file_row.status = "processed"
        file_row.file_size = SEED_FILE.stat().st_size
    session.add(file_row)
    session.commit()
    session.refresh(file_row)

    existing = session.exec(select(KnowledgeChunk).where(KnowledgeChunk.course_id == course.id)).all()
    for row in existing:
        session.delete(row)
    session.commit()

    for idx, chunk in enumerate(chunks):
        content = (chunk.get("content") or "").strip()
        if not content:
            continue
        session.add(
            KnowledgeChunk(
                course_id=int(course.id or 0),
                file_id=int(file_row.id or 0),
                chunk_index=idx,
                content=content,
                source=chunk.get("source") or source_name,
                page_number=chunk.get("page_number"),
                token_count=max(1, len(content) // 2),
            )
        )
    session.commit()
    return len(chunks)


def _seed_profile(session: Session, student: User, data: dict) -> StudentProfile:
    profile = session.exec(select(StudentProfile).where(StudentProfile.user_id == student.id)).first()
    if not profile:
        profile = StudentProfile(user_id=int(student.id or 0))
    for key in (
        "major",
        "learning_goal",
        "knowledge_level",
        "cognitive_style",
        "pace_preference",
        "learning_stage",
        "motivation",
        "meta_learning_level",
        "emotion_tendency",
        "raw_evidence",
        "profile_source",
    ):
        if key in data:
            setattr(profile, key, data[key])
    profile.weak_points = json.dumps(data.get("weak_points", []), ensure_ascii=False)
    profile.resource_preference = json.dumps(data.get("resource_preference", []), ensure_ascii=False)
    profile.profile_confidence = float(data.get("profile_confidence", 0.8))
    profile.profile_version = max(int(profile.profile_version or 1), 1)
    profile.last_extracted_at = datetime.now(timezone.utc)
    profile.updated_at = datetime.now(timezone.utc)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


def _seed_progress(session: Session, student: User, course: Course, data: dict) -> None:
    row = session.exec(
        select(LearningProgress).where(
            LearningProgress.user_id == student.id,
            LearningProgress.course_id == course.id,
        )
    ).first()
    total = int(data.get("total_lessons") or 0)
    completed = int(data.get("completed_lessons") or 0)
    if not row:
        row = LearningProgress(user_id=int(student.id or 0), course_id=int(course.id or 0))
    row.completed_lessons = completed
    row.total_lessons = total
    row.completed_rate = (completed / total) if total else 0.0
    row.weak_points = json.dumps(data.get("weak_points", []), ensure_ascii=False)
    row.next_recommendation = data.get("next_recommendation")
    row.updated_at = datetime.now(timezone.utc)
    session.add(row)


def _seed_quiz_attempts(session: Session, student: User, course: Course, attempts: list[dict]) -> int:
    existing = session.exec(
        select(QuizAttempt).where(
            QuizAttempt.user_id == student.id,
            QuizAttempt.course_id == course.id,
        )
    ).all()
    existing_keys = {(a.question_text, a.knowledge_point) for a in existing}
    added = 0
    for item in attempts:
        key = (item.get("question_text", ""), item.get("knowledge_point", ""))
        if key in existing_keys:
            continue
        session.add(
            QuizAttempt(
                user_id=int(student.id or 0),
                course_id=int(course.id or 0),
                topic=item.get("topic", ""),
                question_text=item.get("question_text", ""),
                selected_answer=item.get("selected_answer", ""),
                correct_answer=item.get("correct_answer", ""),
                is_correct=bool(item.get("is_correct", False)),
                knowledge_point=item.get("knowledge_point", ""),
                explanation=item.get("explanation"),
            )
        )
        existing_keys.add(key)
        added += 1
    return added


def _seed_mastery(session: Session, student: User, course: Course, items: list[dict]) -> None:
    for item in items:
        kp = item.get("knowledge_point") or "知识点"
        row = session.exec(
            select(KnowledgeMastery).where(
                KnowledgeMastery.user_id == student.id,
                KnowledgeMastery.course_id == course.id,
                KnowledgeMastery.knowledge_point == kp,
            )
        ).first()
        if not row:
            row = KnowledgeMastery(user_id=int(student.id or 0), course_id=int(course.id or 0), knowledge_point=kp)
        row.mastery_score = float(item.get("mastery_score", 0.5))
        row.attempt_count = int(item.get("attempt_count", 0))
        row.correct_count = int(item.get("correct_count", 0))
        row.wrong_count = int(item.get("wrong_count", 0))
        row.recommended_action = item.get("recommended_action")
        row.last_practiced_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)
        session.add(row)


def _seed_bookmarks_and_audit(session: Session, student: User, course: Course) -> None:
    bookmark_id = f"demo-course-{course.id}-regularization-package"
    bm = session.exec(
        select(ResourceBookmark).where(
            ResourceBookmark.user_id == student.id,
            ResourceBookmark.resource_id == bookmark_id,
        )
    ).first()
    if not bm:
        session.add(
            ResourceBookmark(
                user_id=int(student.id or 0),
                resource_id=bookmark_id,
                title="过拟合与正则化个性化资源包",
                shared_token="demo-regularization-package",
            )
        )
    session.add(
        AuditLog(
            user_id=int(student.id or 0),
            action="demo_seed",
            target_type="course",
            target_id=str(course.id),
            detail="初始化演示课程、画像、错题、掌握度和 RAG 知识库",
        )
    )


def main() -> int:
    create_db_and_tables()
    data = _load_seed()
    with Session(engine) as session:
        teacher = _get_or_create_user(session, data["teacher"], "teacher")
        student = _get_or_create_user(session, data["student"], "student")
        course = _get_or_create_course(session, teacher, data["course"])
        chunk_count = _seed_course_chunks(session, course, teacher, data.get("chunks", []))
        _seed_profile(session, student, data.get("profile", {}))
        _seed_progress(session, student, course, data.get("progress", {}))
        quiz_added = _seed_quiz_attempts(session, student, course, data.get("quiz_attempts", []))
        _seed_mastery(session, student, course, data.get("mastery", []))
        _seed_bookmarks_and_audit(session, student, course)
        session.commit()

        index_result = build_course_index(int(course.id or 0), session)
        print("=== Demo Data Seeded ===")
        print(f"student_username={student.username}")
        print(f"student_password={data['student']['password']}")
        print(f"teacher_username={teacher.username}")
        print(f"course_id={course.id}")
        print(f"course_name={course.name}")
        print(f"chunks={chunk_count}")
        print(f"quiz_attempts_added={quiz_added}")
        print(f"rag_index={json.dumps(index_result, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
