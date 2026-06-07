"""Student profile API routes for dialogue-based learner profiling."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.auth import get_current_user
from app.core.database import get_session
from app.models.student_profile import StudentProfile
from app.models.student_profile_version import StudentProfileVersion
from app.models.student_profile_change_log import StudentProfileChangeLog
from app.models.user import User
from app.schemas.profiles import (
    ProfileExtractRequest,
    ProfileExtractResponse,
    ProfileResponse,
    ProfileUpdateRequest,
)
from app.services.profile_service import (
    get_or_create_profile,
    update_profile_from_extraction,
)

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


def _profile_to_response(profile: StudentProfile) -> ProfileResponse:
    return ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        major=profile.major,
        learning_goal=profile.learning_goal,
        knowledge_level=profile.knowledge_level,
        cognitive_style=profile.cognitive_style,
        weak_points=profile.weak_points,
        pace_preference=profile.pace_preference,
        learning_stage=profile.learning_stage or "foundation",
        resource_preference=profile.resource_preference,
        motivation=profile.motivation,
        meta_learning_level=profile.meta_learning_level,
        emotion_tendency=profile.emotion_tendency,
        raw_evidence=profile.raw_evidence,
        profile_source=profile.profile_source,
        profile_version=profile.profile_version,
        profile_confidence=profile.profile_confidence,
        last_extracted_at=profile.last_extracted_at,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.get("/me", response_model=ProfileResponse)
def api_get_my_profile(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Get current user's student profile."""
    profile = get_or_create_profile(int(user.id) if user.id else 0, session)
    return _profile_to_response(profile)


@router.post("/me", response_model=ProfileResponse)
def api_update_my_profile(
    body: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Create or update current user's student profile manually."""
    profile = get_or_create_profile(int(user.id) if user.id else 0, session)

    for field, val in body.model_dump(exclude_unset=True).items():
        if val is not None:
            setattr(profile, field, val)

    profile.profile_source = "manual"
    profile.profile_version = int(profile.profile_version or 1) + 1
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return _profile_to_response(profile)


@router.post("/me/extract", response_model=ProfileExtractResponse)
def api_extract_profile(
    body: ProfileExtractRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Extract student profile from natural language description.

    Uses DeepSeek real LLM (with regex rule fallback).
    Saves the extracted profile to the database.
    """
    extracted = update_profile_from_extraction(user, body.message, session, source="dialogue")
    return ProfileExtractResponse(**extracted)


@router.post("/me/confirm")
def api_confirm_profile(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Mark current profile as user-confirmed."""
    profile = get_or_create_profile(int(user.id) if user.id else 0, session)
    profile.profile_source = "confirmed"
    profile.updated_at = datetime.now(timezone.utc)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return {"ok": True, "data": _profile_to_response(profile).model_dump()}


@router.get("/current", response_model=ProfileResponse)
def api_get_current_profile(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    profile = get_or_create_profile(int(user.id) if user.id else 0, session)
    return _profile_to_response(profile)


@router.get("/history")
def api_get_my_profile_history(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    profile = get_or_create_profile(int(user.id) if user.id else 0, session)
    versions = session.exec(
        select(StudentProfileVersion)
        .where(StudentProfileVersion.profile_id == int(profile.id) if profile.id else 0)
        .order_by(StudentProfileVersion.version.desc())
    ).all()
    logs = session.exec(
        select(StudentProfileChangeLog)
        .where(StudentProfileChangeLog.profile_id == int(profile.id) if profile.id else 0)
        .order_by(StudentProfileChangeLog.created_at.desc())
    ).all()
    return {
        "ok": True,
        "data": {
            "profile_id": profile.id,
            "versions": [
                {
                    "id": v.id,
                    "version": v.version,
                    "trigger_source": v.trigger_source,
                    "trigger_text": v.trigger_text,
                    "confidence": v.confidence,
                    "created_at": v.created_at,
                } for v in versions
            ],
            "change_logs": [
                {
                    "id": l.id,
                    "field_name": l.field_name,
                    "old_value": l.old_value,
                    "new_value": l.new_value,
                    "reason": l.reason,
                    "source_type": l.source_type,
                    "source_id": l.source_id,
                    "created_at": l.created_at,
                } for l in logs
            ],
        },
    }


@router.post("/history/{version_id}/restore")
def api_restore_profile_version(
    version_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    profile = get_or_create_profile(int(user.id) if user.id else 0, session)
    version = session.exec(
        select(StudentProfileVersion).where(
            StudentProfileVersion.id == version_id,
            StudentProfileVersion.profile_id == profile.id,
        )
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="profile version not found")
    import json as _json
    snapshot = _json.loads(version.snapshot_json or "{}")
    for field, value in snapshot.items():
        if hasattr(profile, field):
            setattr(profile, field, _json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value)
    profile.profile_version = version.version
    profile.profile_source = "history_restore"
    profile.updated_at = datetime.now(timezone.utc)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return {"ok": True, "data": {"restored_version": version.version, "profile_id": profile.id}}


@router.get("/users/{user_id}", response_model=ProfileResponse)
def api_get_user_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Teacher/admin: view a specific user's profile."""
    if current_user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="only teachers and admins can view other profiles")

    profile = session.exec(
        select(StudentProfile).where(StudentProfile.user_id == user_id)
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")

    return _profile_to_response(profile)
