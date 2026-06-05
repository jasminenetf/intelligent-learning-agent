"""File storage utilities."""

import os
import re
import uuid
from pathlib import Path

from app.core.config import settings

MAX_FILE_SIZE = settings.FILE_UPLOAD_MAX_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def sanitize_filename(filename: str) -> str:
    """Remove path separators and unsafe characters."""
    name = os.path.basename(filename)
    name = re.sub(r"[^\w\.\-]", "_", name)
    if not name or name.startswith("."):
        name = f"file_{uuid.uuid4().hex[:8]}{'' if name.startswith('.') else ''}{name}"
    return name


def validate_file_type(filename: str) -> str:
    """Return lowercase extension if allowed, raise ValueError otherwise."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")
    return ext


def validate_file_size(file_size: int) -> None:
    """Raise ValueError if file exceeds limit."""
    if file_size > MAX_FILE_SIZE:
        max_mb = settings.FILE_UPLOAD_MAX_MB
        raise ValueError(f"file exceeds maximum allowed size of {max_mb}MB")


def save_upload_file(file, course_id: int) -> dict:
    """Save uploaded file to data/raw/{course_id}/ and return metadata."""
    raw_name = file.filename or "unknown"
    safe_name = sanitize_filename(raw_name)
    ext = os.path.splitext(safe_name)[1].lower()

    storage_dir = Path(f"data/raw/{course_id}")
    storage_dir.mkdir(parents=True, exist_ok=True)

    stored_path = str(storage_dir / safe_name)
    # Avoid overwriting: append suffix if exists
    if os.path.exists(stored_path):
        base, ext_part = os.path.splitext(safe_name)
        safe_name = f"{base}_{uuid.uuid4().hex[:6]}{ext_part}"
        stored_path = str(storage_dir / safe_name)

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    validate_file_size(file_size)

    with open(stored_path, "wb") as f:
        f.write(file.file.read())

    return {
        "original_filename": raw_name,
        "safe_filename": safe_name,
        "stored_path": stored_path,
        "file_size": file_size,
        "file_ext": ext,
        "content_type": file.content_type or "",
    }
