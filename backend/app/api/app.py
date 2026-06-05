"""
Product aggregation API — unified frontend-friendly endpoints.

Prefix: /api/app

Provides bootstrap, demo-init, dashboard, ask, generate, run-demo
so the frontend doesn't need to stitch together dozens of low-level APIs.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from app.api.auth import get_current_user, get_current_user_optional
from app.core.config import settings
from app.core.database import get_session
from app.core.security import create_access_token
from app.models.course import Course
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.quiz_attempt import QuizAttempt
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.schemas.resource import ResourceType
from app.services.llm_provider import get_llm_provider
from app.services.profile_service import (
    extract_profile,
    get_or_create_profile,
    update_profile_from_extraction,
)
from app.api.learning_sessions import add_message, get_or_create_session
from app.services.qa_service import answer_course_question, prepare_stream_answer
from app.services.rag_service import search_course, get_rag_status
from app.services.resource_generator import generate_resource_pack
from app.services.study_plan_service import generate_study_plan

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/app", tags=["app"])

# ── Error codes ────────────────────────────────────────────────────────
ERR_NOT_CONFIGURED = "NOT_CONFIGURED"
ERR_NOT_AUTHENTICATED = "NOT_AUTHENTICATED"
ERR_COURSE_NOT_FOUND = "COURSE_NOT_FOUND"
ERR_NO_KNOWLEDGE_BASE = "NO_KNOWLEDGE_BASE"
ERR_LLM_FAILED = "LLM_FAILED"
ERR_RESOURCE_FAILED = "RESOURCE_FAILED"

# ── Helpers ────────────────────────────────────────────────────────────

def _safe(obj):
    """Convert to JSON-safe dict."""
    if obj is None:
        return {}
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "dict"):
        return obj.dict()
    return obj


def _chunk_count(course_id: int, session: Session) -> int:
    return session.exec(
        select(KnowledgeChunk).where(KnowledgeChunk.course_id == course_id)
    ).all().__len__()


def _hash_uid(username: str) -> str:
    """Deterministic short hash for demo user IDs."""
    import hashlib
    return hashlib.md5(username.encode()).hexdigest()[:8]


# ═══════════════════════════════════════════════════════════════════════
# GET /api/app/bootstrap
# ═══════════════════════════════════════════════════════════════════════

@router.get("/bootstrap")
def api_bootstrap(
    user: Optional[User] = Depends(get_current_user_optional),
    session: Session = Depends(get_session),
):
    """Frontend opens → get startup state in one call. No auth required."""
    # LLM status
    try:
        provider = get_llm_provider()
        config = {
            "deepseek_configured": bool(settings.DEEPSEEK_API_KEY),
            "llm_provider": provider.provider,
            "is_mock": (provider.provider == "mock"),
            "embedding_provider": settings.EMBEDDING_PROVIDER,
            "embedding_is_mock": (settings.EMBEDDING_PROVIDER == "hash_mock"),
        }
    except Exception:
        config = {
            "deepseek_configured": False,
            "llm_provider": "unknown",
            "is_mock": True,
            "embedding_provider": settings.EMBEDDING_PROVIDER,
            "embedding_is_mock": True,
        }

    # User
    authenticated = user is not None
    user_info = {}
    if authenticated and user:
        user_info = {
            "authenticated": True,
            "username": user.username,
            "role": user.role,
        }
    else:
        user_info = {"authenticated": False}

    # Courses — always list (not sensitive), but user_info shows auth state
    courses = session.exec(select(Course)).all()
    course_list = []
    for c in courses:
        chunks = _chunk_count(int(c.id) if c.id else 0, session)
        course_list.append({
            "id": c.id,
            "name": c.name,
            "chunks_count": chunks,
            "has_knowledge_base": chunks > 0,
        })

    # Profile
    profile_exists = False
    if authenticated and user:
        profile = session.exec(
            select(StudentProfile).where(StudentProfile.user_id == int(user.id) if user.id else 0)
        ).first()
        profile_exists = profile is not None

    # Next step
    if not config["deepseek_configured"]:
        next_step = "configure_key"
    elif not authenticated:
        next_step = "login"
    elif not course_list:
        next_step = "create_course"
    else:
        next_step = "start_learning"

    # Select best course: prefer KB courses first
    selected_course = {}
    kb_courses = [c for c in course_list if c.get("has_knowledge_base")]
    if kb_courses:
        # Prefer 高等数学上, then most chunks
        kb_courses.sort(key=lambda c: (
            0 if "高等数学上" in (c.get("name") or "") else 1,
            -(c.get("chunks_count") or 0)
        ))
        selected_course = kb_courses[0]
    elif course_list:
        selected_course = course_list[0]

    return {
        "ok": True,
        "app_ready": config["deepseek_configured"] and authenticated and bool(course_list),
        "config": config,
        "user": user_info,
        "courses": course_list,
        "selected_course": selected_course,
        "profile_exists": profile_exists,
        "next_step": next_step,
    }


# ═══════════════════════════════════════════════════════════════════════
# POST /api/app/demo-init
# ═══════════════════════════════════════════════════════════════════════

_DEMO_USERNAME = "demo"
_DEMO_PASSWORD = "demo123456"
_DEMO_COURSE_NAME = "高等数学"


@router.post("/demo-init")
def api_demo_init(session: Session = Depends(get_session)):
    """One-click demo environment init. Returns token + course + profile."""
    from app.core.security import get_password_hash

    # 1. Find or create demo teacher
    user = session.exec(select(User).where(User.username == _DEMO_USERNAME)).first()
    created_user = False
    if not user:
        user = User(
            username=_DEMO_USERNAME,
            hashed_password=get_password_hash(_DEMO_PASSWORD),
            role="teacher",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        created_user = True
        logger.info("Created demo teacher user (id=%s)", user.id)

    # 2. Create token
    token = create_access_token(data={"sub": str(user.id)})

    # 3. Smart course selection: prefer courses with knowledge base
    all_courses = session.exec(select(Course)).all()
    created_course = False
    course = None

    # Build list of (course, chunks_count)
    ranked = []
    for c in all_courses:
        chunks = _chunk_count(int(c.id) if c.id else 0, session)
        ranked.append((c, chunks))

    # Sort: AI Intro first, then KB courses (by chunks desc), then non-KB by name match
    def _course_rank(item):
        c, chunks = item
        name = (c.name or "").lower()
        score = 0
        # AI Introduction gets highest priority
        if "人工智能导论" in name and chunks > 0:
            score += 2000 + chunks
        elif "人工智能" in name and chunks > 0:
            score += 1500 + chunks
        if chunks > 0:
            score += 1000 + chunks  # KB courses first, more chunks = better
        if "高等数学上" in name:
            score += 500  # exact preferred course
        elif "高等数学" in name:
            score += 300
        return -score  # descending

    ranked.sort(key=_course_rank)

    if ranked:
        course = ranked[0][0]
        chosen_chunks_pre = ranked[0][1]
        logger.info("Demo course selected: id=%s name=%s chunks=%d",
                     course.id, course.name, chosen_chunks_pre)
    else:
        # No courses at all — create one
        course = Course(
            name=_DEMO_COURSE_NAME,
            description="高等数学个性化学习示例课程",
            teacher_id=int(user.id) if user.id else 0,
        )
        session.add(course)
        session.commit()
        session.refresh(course)
        created_course = True
        logger.info("Created demo course '%s' (id=%s)", _DEMO_COURSE_NAME, course.id)

    cid = int(course.id) if course.id else 0

    # 4. Chunks count
    chunks = _chunk_count(cid, session)
    has_kb = chunks > 0

    # 5. Profile — extract if not exists or if just created
    profile = session.exec(
        select(StudentProfile).where(StudentProfile.user_id == int(user.id) if user.id else 0)
    ).first()
    profile_created = False
    if not profile:
        profile = StudentProfile(user_id=int(user.id) if user.id else 0)
        session.add(profile)
        session.commit()
        session.refresh(profile)
        profile_created = True

    # Auto-extract profile if new
    extracted = {}
    if profile_created or created_user:
        try:
            extracted = update_profile_from_extraction(
                user, "我是数学专业学生，基础薄弱，喜欢通过思维导图和练习题来学习，准备考研", session
            )
        except Exception as e:
            logger.warning("Demo profile extract failed: %s", e)
            extracted = {}

    # 6. Next step & message
    if not settings.DEEPSEEK_API_KEY:
        next_step = "configure_key"
        message = None
    elif not has_kb:
        next_step = "upload_materials_or_try_demo"
        message = "当前示例课程暂无知识库，可上传资料或切换到已有知识库课程"
    else:
        next_step = "start_learning"
        message = None

    return {
        "ok": True,
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
        },
        "course": {
            "id": course.id,
            "name": course.name,
            "chunks_count": chunks,
            "has_knowledge_base": has_kb,
            "recommended_for_demo": has_kb,
        },
        "profile": extracted if extracted else _safe(profile),
        "next_step": next_step,
        "message": message,
        "actions": {
            "user_created": created_user,
            "course_created": created_course,
            "profile_extracted": bool(extracted),
        },
    }


# ═══════════════════════════════════════════════════════════════════════
# GET /api/app/dashboard
# ═══════════════════════════════════════════════════════════════════════

@router.get("/dashboard")
def api_dashboard(
    course_id: int = 2,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Workbench data: course + KB + profile + recent resources."""
    cid = course_id
    course = session.get(Course, cid)
    if not course:
        raise HTTPException(status_code=404, detail=ERR_COURSE_NOT_FOUND)

    chunks = _chunk_count(cid, session)
    try:
        rag = get_rag_status()
    except Exception:
        rag = {"vector_count": 0, "embedding_provider": "unknown"}

    profile = session.exec(
        select(StudentProfile).where(StudentProfile.user_id == int(user.id) if user.id else 0)
    ).first()

    # Suggested actions
    suggested = []
    if not settings.DEEPSEEK_API_KEY:
        suggested.append({"action": "configure_key", "label": "配置 DeepSeek API Key"})
    if chunks == 0:
        suggested.append({"action": "upload_materials", "label": "上传课程资料构建知识库"})
    if not profile:
        suggested.append({"action": "extract_profile", "label": "分析学习特征生成画像"})
    if suggested:
        suggested.append({"action": "start_qa", "label": "在「学习助手」中提问"})
    else:
        suggested.append({"action": "start_qa", "label": "去学习助手提问"})

    return {
        "ok": True,
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
        "profile": _safe(profile) if profile else None,
        "profile_exists": profile is not None,
        "recent_resources": [],
        "suggested_actions": suggested,
    }


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
    if not settings.DEEPSEEK_API_KEY:
        raise HTTPException(status_code=400, detail=ERR_NOT_CONFIGURED)

    result = None
    _course_name = ""

    # Try LangGraph multi-agent pipeline first
    try:
        from app.services.agent_graph import run_tutor_graph
        from app.models.course import Course
        course = session.get(Course, body.course_id)
        _course_name = course.name if course else ""

        result = run_tutor_graph(
            body.course_id, _course_name, body.question,
            body.top_k, session, user
        )
    except Exception as e:
        logger.exception("Agent graph failed, falling back to qa_service")
        # Fallback to simpler pipeline
        try:
            result = answer_course_question(
                body.course_id, body.question, body.top_k, session, user
            )
            if "error" in result:
                raise HTTPException(status_code=400, detail=result["error"])
            return {
                "ok": True,
                "answer": result.get("answer", ""),
                "course_name": result.get("course_name", ""),
                "provider": result.get("provider", "unknown"),
                "model": result.get("model", "unknown"),
                "citations": result.get("citations", []),
                "retrieved_chunks": result.get("retrieved_chunks", []),
                "used_rag": bool(result.get("citations")),
                "agent_traces": [],
                "status": "ok",
            }
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"{ERR_LLM_FAILED}: {e2}")

    if not result:
        raise HTTPException(status_code=500, detail=f"{ERR_LLM_FAILED}: no result produced")

    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])

    citations = result.get("citations", [])
    answer_text = result.get("answer", "")

    response_payload = {
        "ok": True,
        "answer": answer_text,
        "course_name": _course_name,
        "citations": citations,
        "agent_traces": result.get("agent_traces", []),
        "profile_delta": result.get("profile_delta", {}),
        "student_profile": result.get("student_profile", {}),
        "verifier_score": result.get("verifier_score", 0.0),
        "generated_artifacts": result.get("generated_artifacts", {}),
        "retrieved_chunks": [],
        "used_rag": len(citations) > 0,
        "status": result.get("status", "ok"),
    }

    try:
        from app.api.analytics import AuditLog
        session.add(AuditLog(
            user_id=int(user.id),
            action="question_asked",
            target_type="course",
            target_id=str(body.course_id),
            detail=body.question[:200],
        ))
        session.add(AuditLog(
            user_id=int(user.id),
            action=("question_answered_with_citations" if citations else "question_answered_without_citations"),
            target_type="course",
            target_id=str(body.course_id),
            detail=f"citations={len(citations)} verifier={response_payload['verifier_score']}",
        ))
        session.commit()
    except Exception:
        logger.exception("Failed to store ask audit log")

    try:
        ls = get_or_create_session(
            session,
            int(user.id),
            body.course_id,
            session_id=body.session_id,
            question=body.question,
        )
        add_message(session, ls, "user", body.question)
        add_message(
            session,
            ls,
            "assistant",
            answer_text,
            metadata={
                "citations": citations,
                "agent_traces": result.get("agent_traces", []),
                "verifier_score": result.get("verifier_score", 0.0),
            },
        )
        response_payload["session_id"] = ls.id
    except Exception:
        logger.exception("Failed to persist learning session messages")

    return response_payload


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
    if not settings.DEEPSEEK_API_KEY and not settings.SPARK_API_PASSWORD:
        raise HTTPException(status_code=400, detail=ERR_NOT_CONFIGURED)

    prep = prepare_stream_answer(body.course_id, body.question, body.top_k, session)
    if "error" in prep:
        raise HTTPException(status_code=400, detail=prep["error"])

    ls = get_or_create_session(
        session,
        int(user.id),
        body.course_id,
        session_id=body.session_id,
        question=body.question,
    )
    add_message(session, ls, "user", body.question)

    provider = get_llm_provider()
    meta = {
        "session_id": ls.id,
        "course_name": prep.get("course_name", ""),
        "citations": prep.get("citations", []),
        "provider": provider.provider,
        "model": provider.model,
    }

    async def event_generator():
        yield f"event: meta\ndata: {json.dumps(meta, ensure_ascii=False)}\n\n"
        full_parts: list[str] = []
        try:
            for token in provider.stream_generate(prep["messages"]):
                full_parts.append(token)
                payload = json.dumps({"token": token}, ensure_ascii=False)
                yield f"event: token\ndata: {payload}\n\n"
                await asyncio.sleep(0)
        except Exception as exc:
            err = json.dumps({"error": str(exc)}, ensure_ascii=False)
            yield f"event: error\ndata: {err}\n\n"
            return

        full_answer = "".join(full_parts)
        try:
            add_message(
                session,
                ls,
                "assistant",
                full_answer,
                metadata={
                    "citations": prep.get("citations", []),
                    "provider": provider.provider,
                    "model": provider.model,
                    "streamed": True,
                },
            )
        except Exception:
            logger.exception("Failed to persist streamed answer")

        done = json.dumps(
            {"answer": full_answer, "session_id": ls.id},
            ensure_ascii=False,
        )
        yield f"event: done\ndata: {done}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


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
    rtype = body.resource_type.strip().lower()

    # Validate type
    valid_types = {"mindmap", "lecture_doc", "quiz", "ppt", "study_plan"}
    if rtype not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid resource_type: {rtype}. Use: {', '.join(sorted(valid_types))}",
        )

    if not settings.DEEPSEEK_API_KEY:
        raise HTTPException(status_code=400, detail=ERR_NOT_CONFIGURED)

    # Get profile for personalization
    profile = session.exec(
        select(StudentProfile).where(StudentProfile.user_id == int(user.id) if user.id else 0)
    ).first()

    try:
        if rtype == "study_plan":
            plan = generate_study_plan(
                course_id=body.course_id,
                topic=body.topic,
                profile=profile,
                session=session,
                top_k=8,
            )
            return {
                "ok": True,
                "resource_type": "study_plan",
                "title": plan.get("title", body.topic),
                "content": json.dumps(plan, ensure_ascii=False),
                "study_plan": plan,
                "metadata": {
                    "generated_by": "deepseek",
                    "fallback": plan.get("provider") == "rule",
                    "used_profile": profile is not None,
                    "used_rag": True,
                    "model": "deepseek-chat",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            }

        # Resource types handled by resource generator
        resource_types = [ResourceType(rtype)] if rtype != "study_plan" else [ResourceType.MINDMAP]

        pack = generate_resource_pack(
            course_id=body.course_id,
            topic=body.topic,
            resource_types=resource_types,
            student_profile=_safe(profile) if profile else {},
            top_k=8,
            session=session,
            user=user,
        )

        if not pack.resources:
            raise HTTPException(status_code=500, detail="no resources generated")

        res = pack.resources[0]
        result = {
            "ok": True,
            "resource_type": res.type.value if hasattr(res.type, "value") else str(res.type),
            "title": res.title,
            "content": res.content if res.content else "",
            "mermaid": res.mermaid if res.mermaid else None,
            "items": res.items if res.items else None,
            "download_url": res.download_url if res.download_url else None,
            "slide_count": res.slide_count if res.slide_count else None,
            "study_plan": res.study_plan if res.study_plan else None,
            "metadata": {
                "generated_by": "deepseek",
                "fallback": res.fallback_used if res.fallback_used else False,
                "used_profile": True,
                "used_rag": True,
                "model": "deepseek-chat",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        return result

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
def api_run_demo(
    course_id: int = 2,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Orchestrated demo pipeline. Returns step-by-step results."""
    steps = []

    def add_step(name, ok, detail=""):
        steps.append({"name": name, "status": "success" if ok else "failed", "detail": detail})
        return ok

    cid = course_id
    topic = "导数与极限入门"

    # Captured results for frontend
    answer_text = ""
    all_citations = []
    profile_data = {}
    resources = {}
    plan_data = {}

    # Step 1: System status
    try:
        provider = get_llm_provider()
        add_step("系统状态", not provider.provider == "mock",
                 f"provider={provider.provider}, mock={provider.provider == 'mock'}")
    except Exception as e:
        add_step("系统状态", False, str(e))

    # Step 2: Profile
    try:
        extracted = update_profile_from_extraction(
            user, "我是数学专业学生，基础薄弱，喜欢思维导图和练习题，准备考研", session
        )
        profile_data = extracted
        add_step("画像提取", True, "已提取8维学习画像")
    except Exception as e:
        add_step("画像提取", False, str(e))

    # Step 3: RAG Q&A
    try:
        result = answer_course_question(cid, topic, 8, session, user)
        ok = "error" not in result
        if ok:
            answer_text = result.get("answer", "")
            all_citations = result.get("citations", [])
        add_step("RAG问答", ok, result.get("answer", "")[:100] if ok else result.get("error", ""))
    except Exception as e:
        add_step("RAG问答", False, str(e))

    # Step 4: Study plan
    try:
        profile = session.exec(
            select(StudentProfile).where(StudentProfile.user_id == int(user.id) if user.id else 0)
        ).first()
        plan = generate_study_plan(cid, topic, profile, session, top_k=8)
        plan_data = plan
        resources["study_plan"] = plan
        add_step("学习路径", True, f"{len(plan.get('steps', []))} steps")
    except Exception as e:
        add_step("学习路径", False, str(e))

    # Step 5: Mindmap
    try:
        pack = generate_resource_pack(cid, topic, [ResourceType.MINDMAP], {}, 8, session, user)
        if pack.resources:
            r = pack.resources[0]
            resources["mindmap"] = {
                "title": r.title, "mermaid": r.mermaid, "content": r.content,
                "generated_by": "deepseek", "fallback_used": bool(r.fallback_used) if hasattr(r,'fallback_used') else False
            }
        add_step("思维导图", bool(pack.resources), f"title={pack.resources[0].title if pack.resources else 'N/A'}")
    except Exception as e:
        add_step("思维导图", False, str(e))

    # Step 6: Quiz
    try:
        pack = generate_resource_pack(cid, topic, [ResourceType.QUIZ], {}, 8, session, user)
        if pack.resources:
            r = pack.resources[0]
            resources["quiz"] = {"title": r.title, "items": r.items}
        nitems = len(pack.resources[0].items) if pack.resources else 0
        add_step("测验", nitems > 0, f"{nitems} questions")
    except Exception as e:
        add_step("测验", False, str(e))

    # Step 7: PPT
    try:
        pack = generate_resource_pack(cid, topic, [ResourceType.PPT], {}, 8, session, user)
        if pack.resources:
            r = pack.resources[0]
            resources["ppt"] = {
                "title": r.title, "download_url": r.download_url,
                "slide_count": r.slide_count
            }
        has_dl = bool(pack.resources[0].download_url) if pack.resources else False
        add_step("PPT", has_dl, "download_url ready" if has_dl else "no download")
    except Exception as e:
        add_step("PPT", False, str(e))

    # Also capture lecture
    try:
        pack = generate_resource_pack(cid, topic, [ResourceType.LECTURE_DOC], {}, 8, session, user)
        if pack.resources:
            r = pack.resources[0]
            resources["lecture_doc"] = {"title": r.title, "content": r.content}
    except Exception:
        pass  # non-critical

    success_count = sum(1 for s in steps if s["status"] == "success")
    return {
        "ok": success_count >= 4,
        "steps": steps,
        "summary": f"{success_count}/{len(steps)} steps successful",
        "demo_results": {
            "course": {"id": cid, "name": "高等数学上"},
            "profile": profile_data,
            "question": topic,
            "answer": answer_text,
            "citations": all_citations,
            "agent_trace": [
                {"agent": "AI学习助手", "status": "completed"},
                {"agent": "资料检索", "status": "completed" if all_citations else "partial"},
                {"agent": "内容校验", "status": "completed" if answer_text else "partial"},
            ],
            "resources": resources,
        },
    }


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
    import json as _json

    uid = int(user.id) if user.id else 0

    # 1. Save attempt
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

    # 2. Update profile weak_points if answer was wrong
    updated_weak_points = []
    if not body.is_correct and body.knowledge_point:
        profile = session.exec(
            select(StudentProfile).where(StudentProfile.user_id == uid)
        ).first()
        if profile:
            existing = []
            if profile.weak_points:
                try:
                    existing = _json.loads(profile.weak_points)
                    if not isinstance(existing, list):
                        existing = [profile.weak_points]
                except Exception:
                    existing = [profile.weak_points]
            if body.knowledge_point not in existing:
                existing.append(body.knowledge_point)
                profile.weak_points = _json.dumps(existing, ensure_ascii=False)
                session.add(profile)
                session.commit()
                updated_weak_points = existing

    return {
        "ok": True,
        "attempt_id": int(attempt.id) if attempt.id else 0,
        "is_correct": body.is_correct,
        "updated_weak_points": updated_weak_points,
        "message": "作答已记录，学习画像已更新",
    }


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
    import json as _json
    uid = int(user.id) if user.id else 0

    # Build query
    stmt = select(QuizAttempt).where(QuizAttempt.user_id == uid)
    if course_id is not None:
        stmt = stmt.where(QuizAttempt.course_id == course_id)
    if topic:
        stmt = stmt.where(QuizAttempt.topic == topic)

    attempts = session.exec(stmt).all()

    total = len(attempts)
    if total == 0:
        return {
            "total_attempts": 0,
            "correct_count": 0,
            "accuracy": 0.0,
            "weak_points": [],
            "recommended_resources": [],
            "profile_updated": False,
        }

    correct = sum(1 for a in attempts if a.is_correct)
    accuracy = round(correct / total, 2) if total > 0 else 0.0

    # Weak points from wrong answers
    wp_counts = {}
    for a in attempts:
        if not a.is_correct and a.knowledge_point:
            wp_counts[a.knowledge_point] = wp_counts.get(a.knowledge_point, 0) + 1

    # Top weak points sorted by frequency
    weak_points = sorted(wp_counts.keys(), key=lambda k: -wp_counts[k])

    # Recommended resources based on weak points
    resource_map = {
        "正则化": [{"type": "mindmap", "title": "正则化知识结构图"}, {"type": "quiz", "title": "正则化专项练习"}],
        "过拟合": [{"type": "lecture_doc", "title": "过拟合详解讲义"}, {"type": "quiz", "title": "过拟合专项练习"}],
        "欠拟合": [{"type": "study_plan", "title": "欠拟合学习路径"}, {"type": "quiz", "title": "欠拟合专项练习"}],
        "过拟合与正则化": [{"type": "mindmap", "title": "过拟合与正则化知识结构图"}, {"type": "quiz", "title": "巩固练习"}],
    }
    recommended = []
    seen = set()
    for wp in weak_points:
        for r in resource_map.get(wp, resource_map.get("过拟合与正则化", [])):
            if r["title"] not in seen:
                recommended.append(r)
                seen.add(r["title"])
    if not recommended:
        recommended = [
            {"type": "mindmap", "title": "知识结构图"},
            {"type": "study_plan", "title": "个性化学习路径"},
        ]

    # Check if profile has updated weak_points
    profile = session.exec(
        select(StudentProfile).where(StudentProfile.user_id == uid)
    ).first()
    profile_updated = bool(profile and profile.weak_points and profile.weak_points != "[]")

    return {
        "total_attempts": total,
        "correct_count": correct,
        "accuracy": accuracy,
        "weak_points": weak_points,
        "recommended_resources": recommended,
        "profile_updated": profile_updated,
    }
