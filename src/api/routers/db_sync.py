"""Database sync router — backup/restore SQLite over HTTP.

Designed for environments without persistent disk (e.g. Render free tier).
Push your local DB to the remote deployment, or pull it for backup.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import FileResponse

from src.api.deps import require_auth_or_api_key
from src.api.schemas.envelope import ApiResponse, success_response
from src.config import get_db_url

log = structlog.get_logger()

router = APIRouter(prefix="/db", tags=["database"])


def _db_path() -> Path:
    """Extract filesystem path from the SQLite connection URL."""
    url = get_db_url()
    # sqlite:///path or sqlite:////abs/path
    raw = url.replace("sqlite:///", "", 1)
    return Path(raw).resolve()


@router.get("/backup")
def backup_db(
    _user_id: str = Depends(require_auth_or_api_key),
):
    """Download the current SQLite database file.

    Returns the raw .db file as an attachment.
    """
    db_file = _db_path()
    if not db_file.exists():
        return success_response(data={"error": "Database file not found"})

    return FileResponse(
        path=str(db_file),
        filename="tcg_market.db",
        media_type="application/octet-stream",
    )


@router.post("/restore", response_model=ApiResponse[dict])
async def restore_db(
    file: UploadFile,
    _user_id: str = Depends(require_auth_or_api_key),
):
    """Replace the current SQLite database with an uploaded file.

    The uploaded file must be a valid SQLite database. A backup of the
    current database is created before replacement.

    WARNING: This replaces ALL data. Use with caution.
    """
    db_file = _db_path()

    # Write upload to a temp file first (validates it's complete)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    # Basic SQLite validation: check magic bytes
    magic = content[:16]
    if not magic.startswith(b"SQLite format 3"):
        tmp_path.unlink(missing_ok=True)
        return success_response(
            data={
                "status": "rejected",
                "reason": "Not a valid SQLite file",
            }
        )

    # Backup current DB if it exists
    backup_path = db_file.with_suffix(".db.bak")
    if db_file.exists():
        shutil.copy2(str(db_file), str(backup_path))
        log.info("db_backup_created", path=str(backup_path))

    # Replace DB file
    db_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(tmp_path), str(db_file))

    size_mb = len(content) / (1024 * 1024)
    log.info("db_restored", size_mb=round(size_mb, 2), path=str(db_file))

    return success_response(
        data={
            "status": "restored",
            "size_bytes": len(content),
            "path": str(db_file),
        }
    )
