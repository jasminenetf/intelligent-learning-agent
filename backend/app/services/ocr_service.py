"""OCR service: extract text from scanned PDFs and images.

Uses PyMuPDF for text extraction, with Tesseract OCR fallback for
scanned/image-only pages. The full pipeline: OCR → chunk → SQLite → ChromaDB.

Requires for real OCR (optional, pipeline works without):
  sudo apt install tesseract-ocr tesseract-ocr-chi-sim
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.services.chunker import split_text_to_chunks

logger = logging.getLogger(__name__)

OCR_OUTPUT_DIR = "data/ocr_output"
DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 120

# ── Tesseract detection ────────────────────────────────────────────────────

_tesseract_available: Optional[bool] = None


def _check_tesseract() -> bool:
    """Check if tesseract binary is on PATH. Cached result."""
    global _tesseract_available
    if _tesseract_available is None:
        import shutil
        _tesseract_available = shutil.which("tesseract") is not None
        if _tesseract_available:
            logger.info("OCR: tesseract found on PATH")
        else:
            logger.warning(
                "OCR: tesseract NOT found — scanned/image PDFs will return empty text. "
                "Install: sudo apt install tesseract-ocr tesseract-ocr-chi-sim"
            )
    return _tesseract_available


# ── Data types ─────────────────────────────────────────────────────────────

@dataclass
class OcrPageResult:
    page_number: int
    text: str
    ocr_used: bool = False   # True if OCR fallback was needed
    error: Optional[str] = None


@dataclass
class OcrDocumentResult:
    file_id: int
    course_id: int
    path: str
    pages: list[OcrPageResult] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def total_text(self) -> str:
        return "\n".join(p.text for p in self.pages if p.text)

    @property
    def ocr_page_count(self) -> int:
        return sum(1 for p in self.pages if p.ocr_used)

    @property
    def total_pages(self) -> int:
        return len(self.pages)


# ── Core OCR extraction ───────────────────────────────────────────────────

def extract_text_from_pdf(file_path: str) -> OcrDocumentResult:
    """Extract text from a PDF, using OCR fallback for image-only pages.

    Strategy per page:
      1. PyMuPDF get_text() — works for text-based PDFs
      2. get_textpage_ocr() — Tesseract OCR fallback (requires tesseract)
      3. If both fail, return empty text for that page
    """
    import fitz

    result = OcrDocumentResult(
        file_id=0,
        course_id=0,
        path=file_path,
    )

    if not os.path.exists(file_path):
        result.error = f"file not found: {file_path}"
        return result

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        result.error = f"failed to open PDF: {e}"
        return result

    has_tesseract = _check_tesseract()

    for i, page in enumerate(doc):
        page_num = i + 1
        text = page.get_text("text", sort=True).strip()
        ocr_used = False
        error = None

        # If page is empty (scanned image), try OCR
        if not text and has_tesseract:
            try:
                tp = page.get_textpage_ocr(
                    flags=3,   # 1=text, 2=images → 3=both
                    language="chi_sim+eng",
                    dpi=300,
                    full=True,
                )
                text = page.get_text("text", textpage=tp, sort=True).strip()
                ocr_used = True
            except Exception as e:
                error = str(e)
                text = ""

        result.pages.append(OcrPageResult(
            page_number=page_num,
            text=text,
            ocr_used=ocr_used,
            error=error,
        ))

    doc.close()
    return result


# ── Text saving ────────────────────────────────────────────────────────────

def ensure_ocr_output_dir(course_id: int) -> str:
    """Create and return path to ocr_output/{course_id}/."""
    path = os.path.join(OCR_OUTPUT_DIR, str(course_id))
    os.makedirs(path, exist_ok=True)
    return path


def save_ocr_text(course_id: int, file_id: int, text: str) -> str:
    """Save raw OCR text to data/ocr_output/{course_id}/{file_id}.txt.

    Returns the absolute path to the saved file.
    """
    out_dir = ensure_ocr_output_dir(course_id)
    out_path = os.path.join(out_dir, f"{file_id}.txt")
    Path(out_path).write_text(text, encoding="utf-8")
    logger.info("OCR text saved: %s (%d chars)", out_path, len(text))
    return out_path


# ── Chunk → SQLite → ChromaDB pipeline ─────────────────────────────────────

def ocr_document_to_rag(
    file_id: int,
    course_id: int,
    file_path: str,
    source_label: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    from_session=None,
) -> dict:
    """Full OCR→RAG pipeline for a single file.

    1. Extract text from PDF (PyMuPDF + Tesseract fallback)
    2. Save raw OCR text to data/ocr_output/
    3. Split into chunks
    4. Clean old OCR chunks for this file
    5. Write new chunks to knowledge_chunks (SQLite)
    6. Build ChromaDB index for the course

    Args:
        file_id: CourseFile.id
        course_id: Course.id
        file_path: Absolute path to the PDF file
        source_label: Human-readable source label (e.g. "ocr:高数上.pdf")
        from_session: SQLModel Session (required for DB writes)

    Returns:
        dict with stats: file_id, total_pages, ocr_pages, text_length, chunks, indexed
    """
    # ── 1. OCR ──
    doc_result = extract_text_from_pdf(file_path)
    if doc_result.error:
        return {"error": doc_result.error, "file_id": file_id}

    total_text = doc_result.total_text
    if not total_text.strip():
        return {
            "error": "OCR produced no text — file may be empty or tesseract not installed",
            "file_id": file_id,
            "total_pages": doc_result.total_pages,
            "hint": "Install tesseract: sudo apt install tesseract-ocr tesseract-ocr-chi-sim",
        }

    # ── 2. Save OCR text ──
    save_ocr_text(course_id, file_id, total_text)

    # ── 3. Chunk ──
    text_chunks = split_text_to_chunks(total_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    # ── 4. Clean old OCR chunks + write new chunks ──
    if from_session is None:
        return {"error": "database session required", "file_id": file_id}

    from sqlmodel import delete, select
    from app.models.knowledge_chunk import KnowledgeChunk

    # Delete existing OCR chunks for this file (idempotent)
    # source starts with "ocr:" identifies re-runnable OCR chunks
    deleted = from_session.exec(
        delete(KnowledgeChunk).where(
            KnowledgeChunk.file_id == file_id,
            KnowledgeChunk.source.startswith("ocr:"),
        )
    )

    # Map page numbers: rough heuristic — distribute chunks across pages
    total_pages = max(doc_result.total_pages, 1)
    chunks_per_page = max(1, len(text_chunks) // total_pages)

    chunk_records = []
    for idx, chunk_text in enumerate(text_chunks):
        if not chunk_text.strip():
            continue
        page = (idx // chunks_per_page) + 1
        chunk_records.append(KnowledgeChunk(
            course_id=course_id,
            file_id=file_id,
            chunk_index=idx,
            content=chunk_text,
            source=f"ocr:{source_label}",
            page_number=min(page, total_pages),
        ))

    for rec in chunk_records:
        from_session.add(rec)
    from_session.commit()

    logger.info(
        "OCR→DB: file_id=%d, pages=%d/%d, chunks=%d",
        file_id, doc_result.ocr_page_count, doc_result.total_pages, len(chunk_records),
    )

    # ── 5. Build ChromaDB index ──
    indexed = 0
    try:
        from app.services.rag_service import build_course_index
        build_result = build_course_index(course_id, from_session)
        indexed = build_result.get("indexed_chunks", 0)
    except Exception as e:
        logger.warning("OCR→ChromaDB index failed (non-fatal): %s", e)

    return {
        "file_id": file_id,
        "course_id": course_id,
        "total_pages": doc_result.total_pages,
        "ocr_pages": doc_result.ocr_page_count,
        "text_length": len(total_text),
        "chunks": len(chunk_records),
        "indexed": indexed,
        "ocr_text_path": os.path.join(OCR_OUTPUT_DIR, str(course_id), f"{file_id}.txt"),
    }


def get_ocr_status(file_id: int, course_id: int, session) -> dict:
    """Check OCR status for a file: chunks count, indexed status."""
    from sqlmodel import select
    from app.models.knowledge_chunk import KnowledgeChunk
    from app.services.vector_store import VectorStoreService

    chunks = session.exec(
        select(KnowledgeChunk).where(
            KnowledgeChunk.file_id == file_id,
            KnowledgeChunk.source.startswith("ocr:"),
        )
    ).all()

    # Check ChromaDB
    vs_count = 0
    try:
        from app.services.rag_service import _get_services
        _, vs = _get_services()
        vs_count = vs.count()
    except Exception:
        pass

    return {
        "file_id": file_id,
        "course_id": course_id,
        "ocr_chunks": len(chunks),
        "ocr_text_path": os.path.join(OCR_OUTPUT_DIR, str(course_id), f"{file_id}.txt"),
        "text_exists": os.path.exists(
            os.path.join(OCR_OUTPUT_DIR, str(course_id), f"{file_id}.txt")
        ),
        "chromadb_vectors": vs_count,
        "status": "ready" if chunks else "not_processed",
    }
