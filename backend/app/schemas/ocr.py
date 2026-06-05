"""OCR API request/response schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class OcrExtractRequest(BaseModel):
    """Request to OCR-extract text from a file (without RAG build)."""
    pass  # file_id comes from URL path


class OcrBuildRagResponse(BaseModel):
    """Response from OCR → RAG build for a single file."""
    file_id: int
    course_id: int
    total_pages: int
    ocr_pages: int
    text_length: int
    chunks: int
    indexed: int
    ocr_text_path: str
    status: str = "ok"


class OcrBatchResponse(BaseModel):
    """Response from batch OCR → RAG build for a course."""
    course_id: int
    total_files: int
    processed: int
    failed: int
    results: list[dict]


class OcrStatusResponse(BaseModel):
    """Current OCR status for a file."""
    file_id: int
    course_id: int
    ocr_chunks: int
    ocr_text_path: str
    text_exists: bool
    chromadb_vectors: int
    status: str
