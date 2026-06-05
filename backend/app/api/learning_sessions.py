"""Learning session APIs for persistent tutoring conversations."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.api.auth import get_current_user
from app.core.database import get_session
from app.models.learning_session import ChatMessage, LearningSession
from app.models.user import User

router = APIRouter(prefix="/api/sessions", tags=["learning-sessions"])


class SessionCreateRequest(BaseModel):
    course_id: int = Field(default=0)
    title: str = Field(default="新的学习会话", min_length=1)
    topic: Optional[str] = None


class SessionUpdateRequest(BaseModel):
    title: Optional[str] = None
    topic: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SessionMessageCreateRequest(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


def _touch_session(session_obj: LearningSession) -> LearningSession:
    session_obj.last_message_at = datetime.now(timezone.utc)
    session_obj.updated_at = datetime.now(timezone.utc)
    session_obj.message_count = max(0, session_obj.message_count)
    return session_obj


@router.get("")
def list_sessions(
    course_id: Optional[int] = None,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    stmt = select(LearningSession).where(LearningSession.user_id == int(user.id))
    if course_id is not None:
        stmt = stmt.where(LearningSession.course_id == course_id)
    stmt = stmt.order_by(LearningSession.last_message_at.desc(), LearningSession.id.desc())
    sessions = session.exec(stmt).all()
    return {
        "ok": True,
        "sessions": [
            {
                "id": s.id,
                "course_id": s.course_id,
                "title": s.title,
                "topic": s.topic,
                "summary": s.summary,
                "status": s.status,
                "message_count": s.message_count,
                "last_message_at": s.last_message_at,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
                "metadata": s.metadata or {},
            }
            for s in sessions
        ],
    }


@router.post("")
def create_session(
    body: SessionCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    obj = LearningSession(
        user_id=int(user.id),
        course_id=body.course_id,
        title=body.title,
        topic=body.topic,
        metadata={},
    )
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return {"ok": True, "session": _serialize_session(obj)}


@router.get("/{session_id}")
def get_session_detail(
    session_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    obj = _get_owned_session(session_id, int(user.id), session)
    messages = session.exec(
        select(ChatMessage)
        .where(ChatMessage.session_id == obj.id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
    ).all()
    return {
        "ok": True,
        "session": _serialize_session(obj),
        "messages": [
            {
                "id": m.id,
                "session_id": m.session_id,
                "role": m.role,
                "content": m.content,
                "metadata": m.metadata or {},
                "created_at": m.created_at,
            }
            for m in messages
        ],
    }


@router.patch("/{session_id}")
def update_session(
    session_id: int,
    body: SessionUpdateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    obj = _get_owned_session(session_id, int(user.id), session)
    for field, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(obj, field, value)
    obj.updated_at = datetime.now(timezone.utc)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return {"ok": True, "session": _serialize_session(obj)}


@router.post("/{session_id}/messages")
def add_session_message(
    session_id: int,
    body: SessionMessageCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    obj = _get_owned_session(session_id, int(user.id), session)
    msg = ChatMessage(
        session_id=obj.id,
        role=body.role,
        content=body.content,
        metadata=body.metadata or {},
    )
    obj.message_count = (obj.message_count or 0) + 1
    _touch_session(obj)
    session.add(msg)
    session.add(obj)
    session.commit()
    session.refresh(msg)
    session.refresh(obj)
    return {"ok": True, "message": _serialize_message(msg), "session": _serialize_session(obj)}


# Compatibility helper for app.api.app

def get_or_create_session(
    session: Session,
    user_id: int,
    course_id: int,
    session_id: Optional[int] = None,
    question: Optional[str] = None,
) -> LearningSession:
    if session_id is not None:
        existing = session.get(LearningSession, session_id)
        if existing and existing.user_id == user_id:
            if question:
                existing.topic = existing.topic or question[:60]
                existing.updated_at = datetime.now(timezone.utc)
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing

    title = question[:40] if question else "新的学习会话"
    obj = LearningSession(
        user_id=user_id,
        course_id=course_id,
        title=title or "新的学习会话",
        topic=question[:80] if question else None,
    )
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def add_message(
    session: Session,
    session_obj: LearningSession,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> ChatMessage:
    msg = ChatMessage(
        session_id=session_obj.id,
        role=role,
        content=content,
        metadata=metadata or {},
    )
    session_obj.message_count = (session_obj.message_count or 0) + 1
    session_obj.last_message_at = datetime.now(timezone.utc)
    session_obj.updated_at = datetime.now(timezone.utc)
    session.add(msg)
    session.add(session_obj)
    session.commit()
    session.refresh(msg)
    session.refresh(session_obj)
    return msg


def _get_owned_session(session_id: int, user_id: int, session: Session) -> LearningSession:
    obj = session.get(LearningSession, session_id)
    if not obj or obj.user_id != user_id:
        raise HTTPException(status_code=404, detail="session not found")
    return obj


def _serialize_session(obj: LearningSession) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "user_id": obj.user_id,
        "course_id": obj.course_id,
        "title": obj.title,
        "topic": obj.topic,
        "summary": obj.summary,
        "status": obj.status,
        "message_count": obj.message_count,
        "last_message_at": obj.last_message_at,
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
        "metadata": obj.metadata or {},
    }


def _serialize_message(obj: ChatMessage) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "session_id": obj.session_id,
        "role": obj.role,
        "content": obj.content,
        "metadata": obj.metadata or {},
        "created_at": obj.created_at,
    }
