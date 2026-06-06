"""
Application workspace API.

Prefix: /api/app

Provides bootstrap, dashboard, ask, generate and related
workspace endpoints for the learning product UI.
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
from app.models.quiz_attempt import QuizAttempt
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.schemas.resource import ResourceType
from app.api.learning_sessions import add_message, get_or_create_session
from app.services.llm_provider import get_llm_provider
from app.services.qa_service import answer_course_question, prepare_stream_answer
from app.services.recommendation_service import (
    build_profile_next_actions,
    suggest_resources_from_question,
)
from app.services.resource_generator import generate_resource_pack
from app.services.study_plan_service import generate_study_plan
from app.api.workspace import (
    ok as _ok,
    err as _err,
    safe_obj as _safe,
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
    if not llm_configured():
        _err(ERR_NOT_CONFIGURED, "model service not configured", status_code=400)

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
                _err(ERR_LLM_FAILED, result["error"], status_code=400)
            return _ok({
                "answer": result.get("answer", ""),
                "course_name": result.get("course_name", ""),
                "provider": result.get("provider", "unknown"),
                "model": result.get("model", "unknown"),
                "citations": result.get("citations", []),
                "retrieved_chunks": result.get("retrieved_chunks", []),
                "used_rag": bool(result.get("citations")),
                "agent_traces": [],
                "status": "ok",
            })
        except Exception as e2:
            _err(ERR_LLM_FAILED, str(e2), status_code=500)

    if not result:
        _err(ERR_LLM_FAILED, "no result produced", status_code=500)

    if result.get("error"):
        _err(ERR_LLM_FAILED, result["error"], status_code=400)

    citations = result.get("citations", [])
    answer_text = result.get("answer", "")

    profile_row = session.exec(
        select(StudentProfile).where(StudentProfile.user_id == int(user.id) if user.id else 0)
    ).first()
    resource_suggestions = suggest_resources_from_question(body.question, profile_row)

    response_payload = _ok({
        "answer": answer_text,
        "course_name": _course_name,
        "citations": citations,
        "agent_traces": result.get("agent_traces", []),
        "profile_delta": result.get("profile_delta", {}),
        "student_profile": result.get("student_profile", {}),
        "verifier_score": result.get("verifier_score", 0.0),
        "generated_artifacts": result.get("generated_artifacts", {}),
        "resource_suggestions": resource_suggestions,
        "retrieved_chunks": [],
        "used_rag": len(citations) > 0,
        "status": result.get("status", "ok"),
    })

    if len(body.question.strip()) >= 15:
        try:
            from app.services.profile_service import update_profile_from_extraction

            extracted = update_profile_from_extraction(
                user, body.question, session, source="ask"
            )
            if not response_payload["data"].get("student_profile"):
                response_payload["data"]["student_profile"] = {
                    "knowledge_level": extracted.get("knowledge_level"),
                    "learning_goal": extracted.get("learning_goal"),
                    "weak_points": extracted.get("weak_points"),
                    "emotion_tendency": extracted.get("emotion_tendency"),
                }
        except Exception:
            logger.exception("Failed to update profile from ask")

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
            detail=f"citations={len(citations)} verifier={response_payload.get('data', {}).get('verifier_score', 0.0)}",
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
    if not llm_configured():
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
    citation_count = len(prep.get("citations", []))
    from app.services.agent_graph import build_stream_agent_traces

    agent_traces = build_stream_agent_traces(
        body.question, citation_count, provider.provider, phase="streaming"
    )
    meta = {
        "session_id": ls.id,
        "course_name": prep.get("course_name", ""),
        "citations": prep.get("citations", []),
        "provider": provider.provider,
        "model": provider.model,
        "agent_traces": agent_traces,
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

        from app.services.agent_graph import verify_answer_quality

        verify_result = verify_answer_quality(
            full_answer,
            prep.get("citations", []),
            prep.get("retrieved_chunks", []),
        )
        verifier_score = verify_result["verifier_score"]

        profile_row = session.exec(
            select(StudentProfile).where(StudentProfile.user_id == int(user.id) if user.id else 0)
        ).first()
        resource_suggestions = suggest_resources_from_question(body.question, profile_row)
        final_traces = build_stream_agent_traces(
            body.question,
            citation_count,
            provider.provider,
            phase="done",
            verifier_trace=verify_result.get("trace"),
        )
        generated_artifacts = {
            "ready_for_generation": bool(full_answer),
            "suggestions": resource_suggestions[:5],
        }

        student_profile = {}
        try:
            from app.services.profile_service import (
                update_profile_from_behavior,
                update_profile_from_extraction,
            )
            update_profile_from_behavior(
                user,
                session,
                source="ask",
                text=body.question[:200],
                learning_stage="practice",
                confidence=0.05,
            )
            if len(body.question.strip()) >= 15:
                extracted = update_profile_from_extraction(
                    user, body.question, session, source="ask"
                )
                student_profile = {
                    "knowledge_level": extracted.get("knowledge_level"),
                    "learning_goal": extracted.get("learning_goal"),
                    "weak_points": extracted.get("weak_points"),
                }
        except Exception:
            logger.exception("Failed to update profile after streamed ask")

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

        try:
            from app.api.analytics import AuditLog
            session.add(AuditLog(
                user_id=int(user.id),
                action="question_answered_stream",
                target_type="course",
                target_id=str(body.course_id),
                detail=f"citations={len(prep.get('citations', []))} provider={provider.provider}",
            ))
            session.commit()
        except Exception:
            logger.exception("Failed to store stream ask audit log")

        done = json.dumps(
            {
                "answer": full_answer,
                "session_id": ls.id,
                "citations": prep.get("citations", []),
                "resource_suggestions": resource_suggestions,
                "course_name": prep.get("course_name", ""),
                "provider": provider.provider,
                "model": provider.model,
                "agent_traces": final_traces,
                "verifier_score": verifier_score,
                "student_profile": student_profile,
                "generated_artifacts": generated_artifacts,
            },
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
    valid_types = {"mindmap", "lecture_doc", "quiz", "ppt", "study_plan", "reading", "video_script"}
    if rtype not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid resource_type: {rtype}. Use: {', '.join(sorted(valid_types))}",
        )

    if not llm_configured():
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
            _err(ERR_RESOURCE_FAILED, "no resources generated", status_code=500)

        res = pack.resources[0]
        result = _ok({
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
        })

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
    """Deprecated demo pipeline endpoint."""
    _err("DEPRECATED", "run_demo is deprecated. Use the standard workspace endpoints instead.", status_code=410)
    steps = []

    def add_step(name, ok, detail=""):
        steps.append({"name": name, "status": "success" if ok else "failed", "detail": detail})
        return ok

    cid = course_id
    topic = "导数与极限入门"
    course_name = "高等数学上"

    try:
        course = session.exec(select(Course).where(Course.id == cid)).first()
        if course and course.name:
            course_name = course.name
    except Exception:
        logger.exception("Failed to resolve course name for demo run")

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
    return _ok({
        "steps": steps,
        "summary": f"{success_count}/{len(steps)} steps successful",
        "results": {
            "course": {"id": cid, "name": course_name},
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
    })


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
    try:
        from app.services.profile_service import update_profile_from_behavior
        update_profile_from_behavior(
            user,
            session,
            source="quiz",
            text=body.question_text or body.topic or "quiz_attempt",
            weak_points=updated_weak_points or ([body.knowledge_point] if (not body.is_correct and body.knowledge_point) else []),
            preferred_content=["quiz", "lecture_doc"] if not body.is_correct else ["quiz"],
            learning_goal=None,
            knowledge_level=None,
            cognitive_style="practice_oriented",
            learning_stage="review" if not body.is_correct else "practice",
            learning_pace=None,
            motivation=None,
            confidence=0.2 if not body.is_correct else 0.1,
        )
    except Exception:
        pass

    return _ok({
        "attempt_id": int(attempt.id) if attempt.id else 0,
        "is_correct": body.is_correct,
        "updated_weak_points": updated_weak_points,
        "message": "作答已记录，学习画像已更新",
    })


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

    profile = session.exec(
        select(StudentProfile).where(StudentProfile.user_id == uid)
    ).first()

    total = len(attempts)
    if total == 0:
        next_actions = build_profile_next_actions(profile, [], 0.0) if profile else []
        return _ok({
            "total_attempts": 0,
            "correct_count": 0,
            "accuracy": 0.0,
            "weak_points": [],
            "recommended_resources": [],
            "next_actions": next_actions,
            "profile_summary": {
                "learning_goal": getattr(profile, "learning_goal", None) if profile else None,
                "knowledge_level": getattr(profile, "knowledge_level", None) if profile else None,
            },
            "profile_updated": False,
        })

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

    profile_updated = bool(profile and profile.weak_points and profile.weak_points != "[]")
    next_actions = build_profile_next_actions(profile, weak_points, accuracy)

    try:
        from app.services.profile_service import update_profile_from_behavior
        update_profile_from_behavior(
            user,
            session,
            source="report",
            text=topic or f"course={course_id or 'all'}",
            weak_points=weak_points[:5],
            preferred_content=[r.get("type", "quiz") for r in recommended[:3] if isinstance(r, dict)],
            learning_goal=None,
            knowledge_level=None,
            cognitive_style="logical" if accuracy >= 0.8 else "practice_oriented",
            learning_stage="review" if accuracy < 0.5 else ("practice" if accuracy < 0.8 else "advanced"),
            learning_pace="slow" if accuracy < 0.4 else "moderate",
            motivation=None,
            confidence=0.12,
        )
    except Exception:
        pass

    return _ok({
        "total_attempts": total,
        "correct_count": correct,
        "accuracy": accuracy,
        "weak_points": weak_points,
        "recommended_resources": recommended,
        "next_actions": next_actions,
        "profile_summary": {
            "learning_goal": getattr(profile, "learning_goal", None) if profile else None,
            "knowledge_level": getattr(profile, "knowledge_level", None) if profile else None,
        },
        "profile_updated": profile_updated,
    })
