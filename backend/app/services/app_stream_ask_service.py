"""Streaming workspace Q&A service."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator

from sqlmodel import Session, select

from app.api.learning_sessions import add_message, get_or_create_session
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.services.llm_provider import get_llm_provider
from app.services.qa_service import prepare_stream_answer
from app.services.recommendation_service import suggest_resources_from_question

logger = logging.getLogger(__name__)


def prepare_workspace_stream(*, body: Any, user: User, session: Session) -> tuple[dict[str, Any], Any, Any, dict[str, Any]]:
    """Prepare stream dependencies and emit initial metadata."""
    prep = prepare_stream_answer(body.course_id, body.question, body.top_k, session)
    if "error" in prep:
        return prep, None, None, {}

    learning_session = get_or_create_session(
        session,
        int(user.id),
        body.course_id,
        session_id=body.session_id,
        question=body.question,
    )
    add_message(session, learning_session, "user", body.question)

    provider = get_llm_provider()
    citation_count = len(prep.get("citations", []))
    from app.services.agent_graph import build_stream_agent_traces

    agent_traces = build_stream_agent_traces(
        body.question,
        citation_count,
        provider.provider,
        phase="streaming",
    )
    meta = {
        "session_id": learning_session.id,
        "course_name": prep.get("course_name", ""),
        "citations": prep.get("citations", []),
        "provider": provider.provider,
        "model": provider.model,
        "agent_traces": agent_traces,
    }
    return prep, learning_session, provider, meta


async def workspace_stream_events(*, body: Any, user: User, session: Session, prep: dict[str, Any], learning_session: Any, provider: Any, meta: dict[str, Any]) -> AsyncIterator[str]:
    """Yield SSE events for streamed answer and final metadata."""
    yield f"event: meta\ndata: {json.dumps(meta, ensure_ascii=False)}\n\n"
    full_parts: list[str] = []
    try:
        for token in provider.stream_generate(prep["messages"]):
            full_parts.append(token)
            yield f"event: token\ndata: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)
    except Exception as exc:
        yield f"event: error\ndata: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"
        return

    full_answer = "".join(full_parts)
    done_payload = _finalize_stream_answer(
        body=body,
        user=user,
        session=session,
        prep=prep,
        learning_session=learning_session,
        provider=provider,
        full_answer=full_answer,
    )
    yield f"event: done\ndata: {json.dumps(done_payload, ensure_ascii=False)}\n\n"


def _finalize_stream_answer(*, body: Any, user: User, session: Session, prep: dict[str, Any], learning_session: Any, provider: Any, full_answer: str) -> dict[str, Any]:
    from app.services.agent_graph import build_stream_agent_traces, verify_answer_quality

    verify_result = verify_answer_quality(
        full_answer,
        prep.get("citations", []),
        prep.get("retrieved_chunks", []),
    )
    verifier_score = verify_result["verifier_score"]
    citation_count = len(prep.get("citations", []))

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
    student_profile = _update_stream_profile(body=body, user=user, session=session)
    _persist_stream_answer(session=session, learning_session=learning_session, full_answer=full_answer, prep=prep, provider=provider)
    _store_stream_audit(body=body, user=user, session=session, prep=prep, provider=provider)

    return {
        "answer": full_answer,
        "session_id": learning_session.id,
        "citations": prep.get("citations", []),
        "resource_suggestions": resource_suggestions,
        "course_name": prep.get("course_name", ""),
        "provider": provider.provider,
        "model": provider.model,
        "agent_traces": final_traces,
        "verifier_score": verifier_score,
        "student_profile": student_profile,
        "generated_artifacts": {
            "ready_for_generation": bool(full_answer),
            "suggestions": resource_suggestions[:5],
        },
    }


def _update_stream_profile(*, body: Any, user: User, session: Session) -> dict[str, Any]:
    student_profile: dict[str, Any] = {}
    try:
        from app.services.profile_service import update_profile_from_behavior, update_profile_from_extraction

        update_profile_from_behavior(
            user,
            session,
            source="ask",
            text=body.question[:200],
            learning_stage="practice",
            confidence=0.05,
        )
        if len(body.question.strip()) >= 15:
            extracted = update_profile_from_extraction(user, body.question, session, source="ask")
            student_profile = {
                "knowledge_level": extracted.get("knowledge_level"),
                "learning_goal": extracted.get("learning_goal"),
                "weak_points": extracted.get("weak_points"),
            }
    except Exception:
        logger.exception("Failed to update profile after streamed ask")
    return student_profile


def _persist_stream_answer(*, session: Session, learning_session: Any, full_answer: str, prep: dict[str, Any], provider: Any) -> None:
    try:
        add_message(
            session,
            learning_session,
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


def _store_stream_audit(*, body: Any, user: User, session: Session, prep: dict[str, Any], provider: Any) -> None:
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
