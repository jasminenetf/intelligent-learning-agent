"""Unified resource generation API.

POST /api/resources/courses/{course_id}/generate
GET  /api/resources/download/{resource_id}
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlmodel import Session

from app.api.auth import get_current_user
from app.core.database import get_session
from app.models.user import User
from app.schemas.resource import ResourcePackRequest, ResourcePackResponse
from app.services.generated_file_storage import (
    get_file_content,
    get_file_meta,
    list_generated_files,
    validate_resource_id,
)
from app.services.resource_generator import generate_resource_pack

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
):
    """Download a generated resource file by resource_id.

    Only serves files registered via generated_file_storage.
    Blocks path traversal attempts.
    """
    if not validate_resource_id(resource_id):
        raise HTTPException(status_code=400, detail="invalid resource_id format")

    meta = get_file_meta(resource_id)
    if not meta:
        raise HTTPException(status_code=404, detail="resource not found")

    content = get_file_content(resource_id)
    if content is None:
        raise HTTPException(status_code=404, detail="resource file not found on disk")

    filename = meta.get("original_filename", "download.pptx")
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
):
    """List generated files for the current workspace."""
    return {
        "ok": True,
        "files": list_generated_files(limit=50),
    }
