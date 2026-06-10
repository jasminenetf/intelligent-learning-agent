"""Workspace resource-generation service."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session, select

from app.api.workspace import safe_obj
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.schemas.resource import ResourceType
from app.services.resource_generator import generate_resource_pack
from app.services.study_plan_service import generate_study_plan

VALID_WORKSPACE_RESOURCE_TYPES = {
    "mindmap",
    "lecture_doc",
    "quiz",
    "ppt",
    "study_plan",
    "reading",
    "video_script",
}


def generate_workspace_resource(*, body: Any, user: User, session: Session) -> dict[str, Any]:
    """Generate a workspace resource or study plan for the selected course."""
    rtype = body.resource_type.strip().lower()
    if rtype not in VALID_WORKSPACE_RESOURCE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid resource_type: {rtype}. Use: {', '.join(sorted(VALID_WORKSPACE_RESOURCE_TYPES))}",
        )

    profile = session.exec(
        select(StudentProfile).where(StudentProfile.user_id == int(user.id) if user.id else 0)
    ).first()

    if rtype == "study_plan":
        plan = generate_study_plan(
            course_id=body.course_id,
            topic=body.topic,
            profile=profile,
            session=session,
            top_k=8,
        )
        return {
            "resource_type": "study_plan",
            "title": plan.get("title", body.topic),
            "content": json.dumps(plan, ensure_ascii=False),
            "study_plan": plan,
            "metadata": _resource_metadata(
                fallback=plan.get("provider") == "rule",
                used_profile=profile is not None,
                used_rag=False,
                provider=plan.get("provider") or "rule",
                model=plan.get("model") or "rule",
            ),
        }

    resource_types = [ResourceType(rtype)]
    pack = generate_resource_pack(
        course_id=body.course_id,
        topic=body.topic,
        resource_types=resource_types,
        student_profile=safe_obj(profile) if profile else {},
        top_k=8,
        session=session,
        user=user,
    )

    if not pack.resources:
        raise RuntimeError("no resources generated")

    resource = pack.resources[0]
    return {
        "resource_type": resource.type.value if hasattr(resource.type, "value") else str(resource.type),
        "title": resource.title,
        "content": resource.content if resource.content else "",
        "mermaid": resource.mermaid if resource.mermaid else None,
        "items": resource.items if resource.items else None,
        "download_url": resource.download_url if resource.download_url else None,
        "slide_count": resource.slide_count if resource.slide_count else None,
        "study_plan": resource.study_plan if resource.study_plan else None,
        "metadata": _resource_metadata(
            fallback=bool(resource.fallback_used) if resource.fallback_used else False,
            used_profile=profile is not None,
            used_rag=bool(resource.used_rag),
            provider=pack.provider,
            model=pack.model,
        ),
    }


def _resource_metadata(
    *,
    fallback: bool,
    used_profile: bool,
    used_rag: bool,
    provider: str | None,
    model: str | None,
) -> dict[str, Any]:
    current_provider = provider or ("mock" if fallback else "unknown")
    current_model = model or current_provider
    return {
        "generated_by": current_provider if not fallback else "fallback_template",
        "fallback": fallback,
        "used_profile": used_profile,
        "used_rag": used_rag,
        "model": current_model,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
