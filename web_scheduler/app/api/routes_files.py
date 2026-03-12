from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import get_settings

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> dict:
    settings = get_settings()
    root = Path(settings.uploads_dir)
    root.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "").suffix
    safe_name = f"{uuid4().hex}{suffix}"
    dest = root / safe_name

    try:
        data = await file.read()
        dest.write_bytes(data)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"upload failed: {exc}") from exc

    return {
        "filename": file.filename,
        "saved_name": safe_name,
        "saved_path": str(dest.resolve()),
        "size": len(data),
    }


@router.get("")
def list_uploaded_files() -> list[dict]:
    settings = get_settings()
    root = Path(settings.uploads_dir)
    if not root.exists():
        return []

    rows = []
    for p in sorted(root.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.is_file():
            st = p.stat()
            rows.append({"name": p.name, "path": str(p.resolve()), "size": st.st_size})
    return rows
