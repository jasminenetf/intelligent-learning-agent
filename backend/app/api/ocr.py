"""OCR API routes: extract, build-rag, batch, status."""

from fastapi import APIRouter, Depends, HTTPException, status

from sqlmodel import Session, select

from app.api.auth import get_current_user
from app.core.database import get_session
from app.models.course_file import CourseFile
from app.models.user import User
from app.schemas.ocr import (
    OcrBatchResponse,
    OcrBuildRagResponse,
    OcrStatusResponse,
)
from app.services.ocr_service import (
    get_ocr_status,
    ocr_document_to_rag,
)

router = APIRouter(prefix="/api/ocr", tags=["ocr"])


def _require_teacher_or_admin(user: User):
    if user.role not in ("teacher", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="only teachers and admins can perform this action",
        )


# ── POST /api/ocr/files/{file_id}/build-rag ────────────────────────────

@router.post("/files/{file_id}/build-rag", response_model=OcrBuildRagResponse)
def ocr_build_rag_for_file(
    file_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """OCR a single file and build RAG index in one step.

    Pipeline: OCR → save text → chunk → SQLite knowledge_chunks → ChromaDB.
    Re-running is idempotent: old OCR chunks for this file are cleaned first.
    """
    _require_teacher_or_admin(user)

    cf = session.get(CourseFile, file_id)
    if not cf:
        raise HTTPException(status_code=404, detail="file not found")

    # Only PDFs are supported for OCR (DOCX/TXT already handled by parse_document)
    if cf.file_ext not in (".pdf", ".PDF"):
        raise HTTPException(
            status_code=400,
            detail=f"OCR only supports PDF files, got {cf.file_ext}",
        )

    if not cf.stored_path or not __import__("os").path.exists(cf.stored_path):
        raise HTTPException(status_code=404, detail="stored file not found on disk")

    result = ocr_document_to_rag(
        file_id=cf.id,
        course_id=cf.course_id,
        file_path=cf.stored_path,
        source_label=cf.original_filename,
        from_session=session,
    )

    if "error" in result:
        hint = result.get("hint", "")
        detail = result["error"]
        if hint:
            detail += f". {hint}"
        raise HTTPException(status_code=400, detail=detail)

    # Update file status
    if result.get("chunks", 0) > 0:
        cf.status = "parsed"
        session.add(cf)
        session.commit()

    return OcrBuildRagResponse(**result)


# ── POST /api/ocr/courses/{course_id}/build-rag ─────────────────────────

@router.post("/courses/{course_id}/build-rag", response_model=OcrBatchResponse)
def ocr_build_rag_for_course(
    course_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Batch OCR all PDF files in a course and build RAG index.

    Only processes files with status='failed' (scanned PDFs) or 'uploaded'.
    Files already successfully parsed (status='parsed') are skipped.
    """
    import os as _os  # noqa: F811

    _require_teacher_or_admin(user)

    files = session.exec(
        select(CourseFile).where(
            CourseFile.course_id == course_id,
            CourseFile.file_ext.in_([".pdf", ".PDF"]),
            CourseFile.status.in_(["uploaded", "failed"]),
        )
    ).all()

    if not files:
        return OcrBatchResponse(
            course_id=course_id,
            total_files=0,
            processed=0,
            failed=0,
            results=[],
        )

    results = []
    processed = 0
    failed = 0

    for cf in files:
        if not cf.stored_path or not _os.path.exists(cf.stored_path):
            results.append({"file_id": cf.id, "error": "stored file not found"})
            failed += 1
            continue

        r = ocr_document_to_rag(
            file_id=cf.id,
            course_id=cf.course_id,
            file_path=cf.stored_path,
            source_label=cf.original_filename,
            from_session=session,
        )

        results.append(r)
        if "error" in r:
            failed += 1
        else:
            processed += 1
            if r.get("chunks", 0) > 0:
                cf.status = "parsed"
                session.add(cf)

    session.commit()

    return OcrBatchResponse(
        course_id=course_id,
        total_files=len(files),
        processed=processed,
        failed=failed,
        results=results,
    )


# ── GET /api/ocr/files/{file_id}/status ─────────────────────────────────

@router.get("/files/{file_id}/status", response_model=OcrStatusResponse)
def ocr_file_status(
    file_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Check OCR processing status for a file."""
    cf = session.get(CourseFile, file_id)
    if not cf:
        raise HTTPException(status_code=404, detail="file not found")

    s = get_ocr_status(file_id, cf.course_id, session)
    return OcrStatusResponse(**s)
