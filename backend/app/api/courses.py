"""Course routes: create, list, upload files, list files, list chunks."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlmodel import Session, select

from app.api.auth import get_current_user
from app.core.database import get_session
from app.models.course import Course
from app.models.course_file import CourseFile
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.user import User
from app.schemas.course import (
    ChunkListResponse,
    ChunkRead,
    CourseCreate,
    CourseFileRead,
    CourseFileUploadResponse,
    CourseRead,
)
from app.services.chunker import build_chunk_records
from app.services.document_parser import parse_document
from app.services.file_storage import (
    save_upload_file,
    validate_file_type,
)

router = APIRouter(prefix="/api/courses", tags=["courses"])


def _require_teacher_or_admin(user: User):
    if user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="only teachers and admins can perform this action")


@router.post("", response_model=CourseRead)
def create_course(body: CourseCreate, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    _require_teacher_or_admin(user)
    course = Course(name=body.name, description=body.description, teacher_id=user.id)
    session.add(course)
    session.commit()
    session.refresh(course)
    return course


@router.get("", response_model=list[CourseRead])
def list_courses(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return session.exec(select(Course)).all()


@router.post("/{course_id}/files", response_model=CourseFileUploadResponse)
def upload_course_file(course_id: int, file: UploadFile, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    _require_teacher_or_admin(user)

    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="course not found")

    # Validate file type
    try:
        file_ext = validate_file_type(file.filename or "")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Save file
    try:
        meta = save_upload_file(file, course_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Create CourseFile record
    cf = CourseFile(
        course_id=course_id,
        uploader_id=user.id,
        original_filename=meta["original_filename"],
        stored_path=meta["stored_path"],
        content_type=meta["content_type"],
        file_ext=meta["file_ext"],
        file_size=meta["file_size"],
        status="uploaded",
    )
    session.add(cf)
    session.commit()
    session.refresh(cf)

    # Parse and chunk
    try:
        pages = parse_document(meta["stored_path"], file_ext)
        all_text = "".join(p.text for p in pages)
        if not all_text.strip():
            raise ValueError("empty text or scanned pdf")

        records = build_chunk_records(pages, course_id, cf.id, meta["safe_filename"])
        for rec in records:
            session.add(
                KnowledgeChunk(
                    course_id=rec.course_id,
                    file_id=rec.file_id,
                    chunk_index=rec.chunk_index,
                    content=rec.content,
                    source=rec.source,
                    page_number=rec.page_number,
                )
            )

        cf.status = "parsed"
        chunk_count = len(records)
    except Exception as e:
        cf.status = "failed"
        cf.error_message = str(e)
        chunk_count = 0

    session.add(cf)
    session.commit()
    session.refresh(cf)

    return CourseFileUploadResponse(
        file_id=cf.id,
        course_id=cf.course_id,
        filename=cf.original_filename,
        status=cf.status,
        chunks=chunk_count,
    )


@router.get("/{course_id}/files", response_model=list[CourseFileRead])
def list_course_files(course_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="course not found")
    return session.exec(select(CourseFile).where(CourseFile.course_id == course_id)).all()


@router.get("/{course_id}/chunks", response_model=ChunkListResponse)
def list_course_chunks(course_id: int, limit: int = 20, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    _require_teacher_or_admin(user)
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="course not found")

    chunks = session.exec(
        select(KnowledgeChunk).where(KnowledgeChunk.course_id == course_id).limit(limit)
    ).all()

    return ChunkListResponse(
        course_id=course_id,
        chunks=[
            ChunkRead(
                id=c.id,
                file_id=c.file_id,
                chunk_index=c.chunk_index,
                content=c.content,
                source=c.source,
                page_number=c.page_number,
            )
            for c in chunks
        ],
    )
