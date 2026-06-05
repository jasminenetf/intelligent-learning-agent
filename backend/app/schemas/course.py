"""Course schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CourseCreate(BaseModel):
    name: str
    description: Optional[str] = None


class CourseRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    teacher_id: int
    created_at: datetime


class CourseFileRead(BaseModel):
    id: int
    course_id: int
    uploader_id: int
    original_filename: str
    content_type: str
    file_ext: str
    file_size: int
    status: str
    error_message: Optional[str] = None
    created_at: datetime


class CourseFileUploadResponse(BaseModel):
    file_id: int
    course_id: int
    filename: str
    status: str
    chunks: int


class ChunkRead(BaseModel):
    id: int
    file_id: int
    chunk_index: int
    content: str
    source: str
    page_number: Optional[int] = None


class ChunkListResponse(BaseModel):
    course_id: int
    chunks: list[ChunkRead]
