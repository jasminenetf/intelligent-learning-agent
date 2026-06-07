"""Workspace Q&A service.

Keeps `/api/app/ask` thin by encapsulating agent orchestration,
fallback answering, profile update, recommendations, audit logs and
learning-session persistence.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlmodel import Session, select

from app.api.learning_sessions import add_message, get_or_create_session
from app.api.workspace import err, ok
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.services.content_safety_service import evaluate_content_safety
from app.services.grounding_service import evaluate_grounding
from app.services.qa_service import answer_course_question
from app.services.recommendation_service import suggest_resources_from_question
from app.services.resource_package_service import build_resource_package

logger = logging.getLogger(__name__)

ERR_LLM_FAILED = "LLM_FAILED"


def answer_workspace_question(*, body: Any, user: User, session: Session) -> dict[str, Any]:
    """Run multi-agent Q&A with fallback and side effects."""
    result, course_name = _run_agent_or_fallback(body=body, user=user, session=session)
    if result.get("error"):
        err(ERR_LLM_FAILED, result["error"], status_code=400)

    citations = result.get("citations", [])
    answer_text = result.get("answer", "")
    profile_row = session.exec(
        select(StudentProfile).where(StudentProfile.user_id == int(user.id) if user.id else 0)
    ).first()
    resource_suggestions = suggest_resources_from_question(body.question, profile_row)

    grounding = evaluate_grounding(
        answer=answer_text,
        citations=citations,
        retrieved_chunks=result.get("retrieved_chunks", []),
    )
    safety = evaluate_content_safety(
        question=body.question,
        answer=answer_text,
        citations=citations,
    )

    resource_package = build_resource_package(
        topic=body.question,
        resource_suggestions=resource_suggestions,
        agent_traces=result.get("agent_traces", []),
        grounding=grounding,
        safety=safety,
        mastery=result.get("student_profile", {}),
    )

    response_payload = ok({
        "answer": answer_text,
        "course_name": course_name or result.get("course_name", ""),
        "provider": result.get("provider", "unknown"),
        "model": result.get("model", "unknown"),
        "citations": citations,
        "agent_traces": result.get("agent_traces", []),
        "profile_delta": result.get("profile_delta", {}),
        "student_profile": result.get("student_profile", {}),
        "verifier_score": result.get("verifier_score", 0.0),
        "grounding_score": grounding.get("grounding_score", 0.0),
        "grounding": grounding,
        "content_safety": safety,
        "generated_artifacts": result.get("generated_artifacts", {}),
        "resource_suggestions": resource_suggestions,
        "resource_package": resource_package,
        "retrieved_chunks": result.get("retrieved_chunks", []),
        "used_rag": bool(citations),
        "status": result.get("status", "ok"),
    })

    _update_profile_from_question(body=body, user=user, session=session, response_payload=response_payload)
    _store_ask_audit(body=body, user=user, session=session, citations=citations, response_payload=response_payload)
    _persist_ask_messages(body=body, user=user, session=session, answer_text=answer_text, result=result, response_payload=response_payload)
    return response_payload


def _run_agent_or_fallback(*, body: Any, user: User, session: Session) -> tuple[dict[str, Any], str]:
    course_name = ""
    try:
        from app.models.course import Course
        from app.services.agent_graph import run_tutor_graph

        course = session.get(Course, body.course_id)
        course_name = course.name if course else ""
        result = run_tutor_graph(
            body.course_id,
            course_name,
            body.question,
            body.top_k,
            session,
            user,
        )
        if not result:
            err(ERR_LLM_FAILED, "no result produced", status_code=500)
        return result, course_name
    except Exception:
        logger.exception("Agent graph failed, falling back to qa_service")
        try:
            result = answer_course_question(
                body.course_id,
                body.question,
                body.top_k,
                session,
                user,
            )
            if result.get("error"):
                err(ERR_LLM_FAILED, result["error"], status_code=400)
            result.setdefault("agent_traces", [])
            result.setdefault("status", "ok")
            return result, result.get("course_name", course_name)
        except Exception as exc:
            err(ERR_LLM_FAILED, str(exc), status_code=500)
    return {}, course_name


def _update_profile_from_question(*, body: Any, user: User, session: Session, response_payload: dict[str, Any]) -> None:
    if len(body.question.strip()) < 15:
        return
    try:
        from app.services.profile_service import update_profile_from_extraction

        extracted = update_profile_from_extraction(
            user,
            body.question,
            session,
            source="ask",
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


def _store_ask_audit(*, body: Any, user: User, session: Session, citations: list[Any], response_payload: dict[str, Any]) -> None:
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


def _persist_ask_messages(*, body: Any, user: User, session: Session, answer_text: str, result: dict[str, Any], response_payload: dict[str, Any]) -> None:
    try:
        learning_session = get_or_create_session(
            session,
            int(user.id),
            body.course_id,
            session_id=body.session_id,
            question=body.question,
        )
        add_message(session, learning_session, "user", body.question)
        add_message(
            session,
            learning_session,
            "assistant",
            answer_text,
            metadata={
                "citations": result.get("citations", []),
                "agent_traces": result.get("agent_traces", []),
                "verifier_score": result.get("verifier_score", 0.0),
            },
        )
        response_payload["session_id"] = learning_session.id
    except Exception:
        logger.exception("Failed to persist learning session messages")
