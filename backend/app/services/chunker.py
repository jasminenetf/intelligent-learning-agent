"""Text chunking with plain Python (no external dependency)."""

from dataclasses import dataclass
from typing import Optional

from app.services.document_parser import ParsedPage

DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 120


@dataclass
class ChunkRecord:
    course_id: int
    file_id: int
    chunk_index: int
    content: str
    source: str
    page_number: Optional[int] = None


def split_text_to_chunks(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks by character count."""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - chunk_overlap
        if start >= len(text):
            break
    return chunks


def build_chunk_records(pages: list[ParsedPage], course_id: int, file_id: int, source: str) -> list[ChunkRecord]:
    records = []
    chunk_index = 0
    for page in pages:
        if not page.text:
            continue
        chunks = split_text_to_chunks(page.text)
        for ch in chunks:
            records.append(
                ChunkRecord(
                    course_id=course_id,
                    file_id=file_id,
                    chunk_index=chunk_index,
                    content=ch,
                    source=source,
                    page_number=page.page_number if page.page_number > 0 else None,
                )
            )
            chunk_index += 1
    return records
