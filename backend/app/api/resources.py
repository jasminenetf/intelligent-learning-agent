"""Unified resource generation API.

POST /api/resources/courses/{course_id}/generate
GET  /api/resources/download/{resource_id}
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlmodel import Session, select

from app.api.auth import get_current_user
from app.core.database import get_session
from app.models.resource_artifact import ResourceArtifact
from app.models.user import User
from app.schemas.resource import ResourcePackRequest, ResourcePackResponse
from app.services.generated_file_storage import (
    get_file_content,
    get_file_meta,
    list_generated_files,
    validate_resource_id,
)
from app.services.resource_generator import generate_resource_pack
from app.services.resource_orchestrator import generate_resource_pack_orchestrated, get_resource_job

router = APIRouter(prefix="/api/resources", tags=["resources"])


@router.post("/courses/{course_id}/generate", response_model=ResourcePackResponse)
def api_generate_resources(
    course_id: int,
    body: ResourcePackRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Generate educational resources for a course topic.

    Supported resource_types: mindmap, lecture_doc, quiz, ppt.
    """
    try:
        result = generate_resource_pack(
            course_id=course_id,
            topic=body.topic,
            resource_types=list(body.resource_types),
            student_profile=body.student_profile.model_dump(),
            top_k=body.top_k,
            session=session,
            user=user,
        )
        return result
    except ValueError as e:
        msg = str(e)
        if "course not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        if "no relevant" in msg:
            raise HTTPException(status_code=400, detail=msg)
        raise HTTPException(status_code=500, detail=msg)


@router.get("/download/{resource_id}")
def api_download_resource(
    resource_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Download a generated resource file by resource_id.

    Only serves files registered via generated_file_storage.
    Blocks path traversal attempts.
    """
    if not validate_resource_id(resource_id):
        raise HTTPException(status_code=400, detail="invalid resource_id format")

    meta = get_file_meta(resource_id)
    artifact = session.exec(
        select(ResourceArtifact).where(
            ResourceArtifact.download_resource_id == resource_id,
            ResourceArtifact.user_id == int(user.id) if user.id else 0,
        )
    ).first()
    if not meta and not artifact:
        raise HTTPException(status_code=404, detail="resource not found")
    if meta and not artifact:
        # Legacy registry files have no owner metadata. Restrict them to admins to avoid cross-user leakage.
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="resource ownership required")

    content = get_file_content(resource_id)
    if content is None:
        raise HTTPException(status_code=404, detail="resource file not found on disk")

    filename = (meta or {}).get("original_filename") or (artifact.title if artifact else None) or "download.pptx"
    # URL-encode non-ASCII filename for Content-Disposition
    import urllib.parse
    safe_name = urllib.parse.quote(filename, safe="")

    return Response(
        content=content,
        media_type=meta.get("content_type", "application/octet-stream"),
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}",
        },
    )


@router.get("/generated")
def api_list_generated_files(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """List generated files for the current workspace."""
    uid = int(user.id) if user.id else 0
    artifacts = session.exec(
        select(ResourceArtifact)
        .where(ResourceArtifact.user_id == uid)
        .order_by(ResourceArtifact.created_at.desc(), ResourceArtifact.id.desc())
        .limit(50)
    ).all()
    files = list_generated_files(limit=50) if user.role == "admin" else []
    artifact_items = [
        {
            "resource_id": a.download_resource_id or a.artifact_id,
            "artifact_id": a.artifact_id,
            "job_id": a.job_id,
            "original_filename": a.title,
            "filename": a.title,
            "content_type": a.resource_type,
            "size": len(a.content or ""),
            "status": "ready",
            "created_at": a.created_at,
            "quality_score": a.quality_score,
            "topic": a.topic,
        }
        for a in artifacts
    ]
    return {
        "ok": True,
        "files": files + artifact_items,
    }


@router.post("/generate")
def api_generate_orchestrated(
    body: dict,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Multi-agent orchestrated resource generation."""
    course_id = int(body.get("course_id") or 0)
    topic = (body.get("topic") or "").strip()
    resource_types = body.get("resource_types") or ["lecture_doc", "mindmap", "quiz"]
    if not course_id or not topic:
        raise HTTPException(status_code=400, detail="course_id and topic are required")
    return generate_resource_pack_orchestrated(
        user=user,
        session=session,
        course_id=course_id,
        topic=topic,
        resource_types=list(resource_types),
        difficulty=body.get("difficulty", "auto"),
        goal=body.get("goal"),
        top_k=int(body.get("top_k") or 5),
    )


@router.get("/generate/{job_id}")
def api_get_generation_job(
    job_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    uid = int(user.id) if user.id else 0
    job = get_resource_job(job_id, uid, session)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return {"ok": True, "data": job}


@router.get("/jobs")
def api_list_generation_jobs(
    limit: int = 20,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    from app.models.resource_job import ResourceJob

    uid = int(user.id) if user.id else 0
    rows = session.exec(
        select(ResourceJob)
        .where(ResourceJob.user_id == uid)
        .order_by(ResourceJob.created_at.desc(), ResourceJob.id.desc())
        .limit(limit)
    ).all()
    return {
        "ok": True,
        "data": {
            "items": [
                {
                    "job_id": r.job_id,
                    "course_id": r.course_id,
                    "topic": r.topic,
                    "status": r.status,
                    "progress": r.progress,
                    "current_agent": r.current_agent,
                    "created_at": r.created_at,
                }
                for r in rows
            ]
        },
    }
