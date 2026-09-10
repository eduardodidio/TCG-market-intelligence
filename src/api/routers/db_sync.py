"""Database sync router — backup/restore SQLite over HTTP.

Designed for environments without persistent disk (e.g. Render free tier).
Push your local DB to the remote deployment, or pull it for backup.
"""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from src.api.deps import require_auth_or_api_key
from src.api.schemas.envelope import ApiResponse, success_response
from src.config import get_db_url

log = structlog.get_logger()

router = APIRouter(prefix="/db", tags=["database"])

# Monotonic version counter — incremented on each DB restore.
# Frontend reads this via the X-DB-Version response header and reloads
# when it detects a change, fixing the stale-cache-after-push-db bug.
_db_version: int = 1


def get_db_version() -> int:
    """Return the current DB version counter."""
    return _db_version


def bump_db_version() -> int:
    """Increment and return the DB version counter."""
    global _db_version
    _db_version += 1
    return _db_version


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
    if not get_db_url().startswith("sqlite"):
        raise HTTPException(400, "DB file sync not needed — using persistent PostgreSQL database.")
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
    if not get_db_url().startswith("sqlite"):
        raise HTTPException(400, "DB file sync not needed — using persistent PostgreSQL database.")
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

    # Log collection counts from current DB before replacing
    pre_restore_stats = _count_db_rows(db_file)
    if pre_restore_stats:
        log.info(
            "db_restore_pre_stats",
            users=pre_restore_stats.get("users", 0),
            collection_entries=pre_restore_stats.get("collection_entries", 0),
            cards=pre_restore_stats.get("cards", 0),
        )

    # Backup current DB if it exists — both .bak (latest) and timestamped
    backup_path: Path | None = None
    if db_file.exists():
        # Always keep the latest backup as .bak
        backup_path = db_file.with_suffix(".db.bak")
        shutil.copy2(str(db_file), str(backup_path))
        log.info("db_backup_created", path=str(backup_path))

        # Also create a timestamped backup to prevent overwriting previous ones
        ts = datetime.now().strftime("%Y%m%dT%H%M%S")
        ts_backup = db_file.with_suffix(f".db.bak.{ts}")
        shutil.copy2(str(db_file), str(ts_backup))
        log.info("db_backup_timestamped", path=str(ts_backup))

    # Replace DB file
    db_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(tmp_path), str(db_file))

    # Log collection counts from the NEW (restored) DB
    post_restore_stats = _count_db_rows(db_file)
    if post_restore_stats:
        log.info(
            "db_restore_post_stats",
            users=post_restore_stats.get("users", 0),
            collection_entries=post_restore_stats.get("collection_entries", 0),
            cards=post_restore_stats.get("cards", 0),
        )
        # Warn if collection entries dropped to zero
        pre_count = pre_restore_stats.get("collection_entries", 0) if pre_restore_stats else 0
        post_count = post_restore_stats.get("collection_entries", 0)
        if pre_count > 0 and post_count == 0:
            log.warning(
                "db_restore_collection_lost",
                pre_count=pre_count,
                post_count=post_count,
                message="Collection entries were lost during restore! Check timestamped backup.",
            )

    # Remove stale WAL/SHM files — they reference the OLD database and
    # will corrupt connections to the newly restored file.
    for suffix in (".db-wal", ".db-shm"):
        stale = db_file.with_suffix(suffix)
        if stale.exists():
            stale.unlink()
            log.info("db_stale_file_removed", path=str(stale))

    # Invalidate cached singletons so new requests use the restored DB
    _invalidate_db_caches()

    # Bump DB version so frontend detects the change via X-DB-Version header
    new_version = bump_db_version()
    log.info("db_version_bumped", version=new_version)

    size_mb = len(content) / (1024 * 1024)
    log.info("db_restored", size_mb=round(size_mb, 2), path=str(db_file))

    return success_response(
        data={
            "status": "restored",
            "size_bytes": len(content),
            "path": str(db_file),
            "backup_path": str(backup_path) if backup_path else None,
        }
    )


def _invalidate_db_caches() -> None:
    """Clear singleton caches that hold Repository/engine references.

    After a DB file replacement, SQLAlchemy engines still point at the
    old (now replaced) file via connection pool.  Disposing them forces
    new connections on the next request.
    """
    from src.api.deps import _create_market_data_service, get_provider_registry

    # Dispose MarketDataService singleton engine
    if hasattr(_create_market_data_service, "_instance"):
        try:
            _create_market_data_service._instance.repo.engine.dispose()
        except Exception:
            pass
        del _create_market_data_service._instance
        log.info("db_cache_invalidated", target="market_data_service")

    # Provider registry doesn't hold a DB connection, but clear for safety
    if hasattr(get_provider_registry, "_instance"):
        del get_provider_registry._instance

    log.info("db_caches_cleared")


def _count_db_rows(db_path: Path) -> dict | None:
    """Count key rows in a SQLite DB file for restore diagnostics.

    Returns None if the file does not exist or is not readable.
    """
    if not db_path.exists():
        return None
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        tables = {
            row[0]
            for row in cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        stats: dict[str, int] = {}
        if "users" in tables:
            stats["users"] = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if "user_collection" in tables:
            stats["collection_entries"] = cursor.execute(
                "SELECT COUNT(*) FROM user_collection"
            ).fetchone()[0]
        if "cards" in tables:
            stats["cards"] = cursor.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
        conn.close()
        return stats
    except Exception:
        log.warning("db_count_rows_failed", path=str(db_path), exc_info=True)
        return None
