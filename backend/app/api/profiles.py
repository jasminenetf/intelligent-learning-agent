"""Student profile API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.auth import get_current_user
from app.core.database import get_session
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.schemas.profiles import (
    ProfileExtractRequest,
    ProfileExtractResponse,
    ProfileResponse,
    ProfileUpdateRequest,
)
from app.services.profile_service import (
    extract_profile,
    get_or_create_profile,
    update_profile_from_extraction,
)

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@router.get("/me", response_model=ProfileResponse)
def api_get_my_profile(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Get current user's student profile."""
    profile = get_or_create_profile(int(user.id) if user.id else 0, session)
    return profile


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

    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


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
    extracted = update_profile_from_extraction(user, body.message, session)
    return ProfileExtractResponse(**extracted)


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

    return profile
