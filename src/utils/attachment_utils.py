from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


def save_uploaded_file(uploaded_file: FileStorage | None, uploads_dir: Path) -> dict | None:
    if uploaded_file is None:
        return None

    original_name = secure_filename(uploaded_file.filename or "").strip()
    if not original_name:
        return None

    uploads_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(original_name).suffix
    stored_name = f"{uuid4().hex}{suffix}"
    stored_path = uploads_dir / stored_name
    uploaded_file.save(stored_path)

    return {
        "temp_path": str(stored_path),
        "original_name": original_name,
        "content_type": (uploaded_file.mimetype or "application/octet-stream").strip() or "application/octet-stream",
        "size": stored_path.stat().st_size,
    }


def delete_temp_file(path_value: str | None) -> None:
    if not path_value:
        return
    try:
        path = Path(path_value)
        if path.exists():
            path.unlink()
    except OSError:
        return
