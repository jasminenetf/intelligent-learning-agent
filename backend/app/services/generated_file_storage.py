"""Generated file storage: save, register, retrieve, and serve generated files.

Files are stored under data/generated/ (gitignored).
Each file gets a unique resource_id for download.
The registry is persisted to disk so downloads still work after restart.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.core.config import settings

GENERATED_DIR = Path(settings.GENERATED_DIR)
REGISTRY_PATH = GENERATED_DIR / "registry.json"

# In-memory registry: resource_id → metadata
_registry: dict[str, dict] = {}


def _ensure_dir() -> Path:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    return GENERATED_DIR


def _load_registry() -> None:
    _ensure_dir()
    if not REGISTRY_PATH.exists():
        return
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            _registry.update(data)
    except Exception:
        # Corrupted registry should not break file generation
        pass


def _persist_registry() -> None:
    _ensure_dir()
    REGISTRY_PATH.write_text(
        json.dumps(_registry, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_generated_file(
    content: bytes,
    filename: str,
    content_type: str = "application/octet-stream",
) -> dict:
    """Save a generated file and register it for download.

    Args:
        content: File bytes.
        filename: Suggested filename.
        content_type: MIME type.

    Returns:
        dict with resource_id, filename, download_url.
    """
    _ensure_dir()

    resource_id = f"gen_{uuid.uuid4().hex[:12]}"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_name = f"{timestamp}_{resource_id}_{_sanitize_filename(filename)}"
    filepath = GENERATED_DIR / safe_name

    filepath.write_bytes(content)

    meta = {
        "resource_id": resource_id,
        "filename": safe_name,
        "original_filename": filename,
        "filepath": str(filepath),
        "content_type": content_type,
        "size": len(content),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _registry[resource_id] = meta
    _persist_registry()

    return {
        "resource_id": resource_id,
        "filename": safe_name,
        "download_url": f"/api/resources/download/{resource_id}",
        "size": meta["size"],
    }


def list_generated_files(limit: int = 50) -> list[dict]:
    """Return newest generated files for the current workspace."""
    _load_registry()
    items = sorted(
        _registry.values(),
        key=lambda x: x.get("created_at", ""),
        reverse=True,
    )
    return items[:limit]


def get_file_meta(resource_id: str) -> Optional[dict]:
    """Get metadata for a registered file."""
    _load_registry()
    return _registry.get(resource_id)


def get_file_content(resource_id: str) -> Optional[bytes]:
    """Read and return the file content for a registered resource_id."""
    _load_registry()
    meta = _registry.get(resource_id)
    if not meta:
        return None

    filepath = Path(meta["filepath"])
    if not filepath.exists():
        return None

    return filepath.read_bytes()


def validate_resource_id(resource_id: str) -> bool:
    """Check that resource_id is safe (no path traversal)."""
    import re
    return bool(re.match(r"^[a-zA-Z0-9_-]+$", resource_id))


def _sanitize_filename(name: str) -> str:
    """Remove path separators and dangerous characters from filename."""
    import re
    name = re.sub(r"[\\/:\"*?<>|]", "_", name)
    return name[:100]
