"""Workspace API helpers for the learning product UI.

This module centralizes shared response helpers and course/profile lookup
logic used by the `/api/app` workspace endpoints.
"""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.config import settings
from app.models.course import Course
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.services.llm_provider import get_llm_provider
from app.services.rag_service import get_rag_status


def safe_obj(obj):
    if obj is None:
        return {}
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "dict"):
        return obj.dict()
    return obj


def ok(data=None, **meta):
    payload = {"ok": True, "data": data if data is not None else {}}
    if meta:
        payload.update(meta)
    return payload


def err(code: str, message: str, status_code: int = 400, **meta):
    detail = {"code": code, "message": message}
    if meta:
        detail.update(meta)
    raise HTTPException(status_code=status_code, detail=detail)


def chunk_count(course_id: int, session: Session) -> int:
    return session.exec(
        select(KnowledgeChunk).where(KnowledgeChunk.course_id == course_id)
    ).all().__len__()


def llm_configured() -> bool:
    return bool(
        settings.DEEPSEEK_API_KEY
        or settings.SPARK_API_PASSWORD
        or settings.SPARK_API_KEY
    )


def bootstrap_payload(user: Optional[User], session: Session):
    configured = llm_configured()
    try:
        provider = get_llm_provider()
        config = {
            "deepseek_configured": bool(settings.DEEPSEEK_API_KEY),
            "spark_configured": bool(settings.SPARK_API_PASSWORD or settings.SPARK_API_KEY),
            "llm_configured": configured,
            "llm_provider": provider.provider,
            "is_mock": (provider.provider == "mock"),
            "embedding_provider": settings.EMBEDDING_PROVIDER,
            "embedding_is_mock": (settings.EMBEDDING_PROVIDER == "hash_mock"),
        }
    except Exception:
        config = {
            "deepseek_configured": False,
            "spark_configured": False,
            "llm_configured": configured,
            "llm_provider": "unknown",
            "is_mock": True,
            "embedding_provider": settings.EMBEDDING_PROVIDER,
            "embedding_is_mock": True,
        }

    authenticated = user is not None
    user_info = {
        "authenticated": bool(authenticated),
        "username": user.username if authenticated and user else None,
        "role": user.role if authenticated and user else None,
    }

    courses = session.exec(select(Course)).all()
    course_list = []
    for c in courses:
        chunks = chunk_count(int(c.id) if c.id else 0, session)
        course_list.append({
            "id": c.id,
            "name": c.name,
            "chunks_count": chunks,
            "has_knowledge_base": chunks > 0,
        })

    profile_exists = False
    if authenticated and user:
        profile = session.exec(
            select(StudentProfile).where(StudentProfile.user_id == int(user.id) if user.id else 0)
        ).first()
        profile_exists = profile is not None

    if not config["llm_configured"]:
        next_step = "configure_key"
    elif not authenticated:
        next_step = "login"
    elif not course_list:
        next_step = "create_course"
    else:
        next_step = "start_learning"

    selected_course = {}
    kb_courses = [c for c in course_list if c.get("has_knowledge_base")]
    if kb_courses:
        kb_courses.sort(key=lambda c: (
            0 if "高等数学上" in (c.get("name") or "") else 1,
            -(c.get("chunks_count") or 0)
        ))
        selected_course = kb_courses[0]
    elif course_list:
        selected_course = course_list[0]

    return ok({
        "app_ready": config["llm_configured"] and authenticated and bool(course_list),
        "config": config,
        "user": user_info,
        "courses": course_list,
        "selected_course": selected_course,
        "profile_exists": profile_exists,
        "next_step": next_step,
    })


def dashboard_payload(course_id: Optional[int], user: User, session: Session):
    cid = course_id
    if cid is None:
        courses = session.exec(select(Course)).all()
        if not courses:
            err("COURSE_NOT_FOUND", "course not found", status_code=404)
        course = courses[0]
        cid = int(course.id) if course.id else 0
    else:
        course = session.get(Course, cid)
        if not course:
            err("COURSE_NOT_FOUND", "course not found", status_code=404)

    chunks = chunk_count(cid, session)
    try:
        rag = get_rag_status()
    except Exception:
        rag = {"vector_count": 0, "embedding_provider": "unknown"}

    profile = session.exec(
        select(StudentProfile).where(StudentProfile.user_id == int(user.id) if user.id else 0)
    ).first()

    suggested = []
    if not llm_configured():
        suggested.append({"action": "configure_key", "label": "配置模型服务"})
    if chunks == 0:
        suggested.append({"action": "upload_materials", "label": "上传课程资料构建知识库"})
    if not profile:
        suggested.append({"action": "extract_profile", "label": "通过对话构建学习画像"})
    suggested.append({"action": "start_qa", "label": "进入学习助手提问"})
    suggested.append({"action": "generate_resources", "label": "生成讲义、导图、题库等资源"})

    return ok({
        "course": {
            "id": course.id,
            "name": course.name,
            "description": course.description,
        },
        "knowledge_base": {
            "chunks_count": chunks,
            "vector_ready": rag.get("vector_count", 0) > 0,
            "vector_count": rag.get("vector_count", 0),
            "status": "ready" if chunks > 0 else "no_data",
        },
        "profile": safe_obj(profile) if profile else None,
        "profile_exists": profile is not None,
        "recent_resources": [],
        "suggested_actions": suggested,
    })
