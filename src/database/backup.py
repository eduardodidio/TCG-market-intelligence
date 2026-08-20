"""Database backup utility using the sqlite3.backup() API."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import structlog

log = structlog.get_logger()


def extract_db_path(db_url: str) -> str:
    """Extract the file path from a SQLAlchemy SQLite URL.

    ``sqlite:///tcg_market.db`` -> ``tcg_market.db``
    ``sqlite:////absolute/path.db`` -> ``/absolute/path.db``
    """
    prefix = "sqlite:///"
    if not db_url.startswith(prefix):
        raise ValueError(f"Unsupported database URL: {db_url!r} (expected sqlite:///...)")
    return db_url[len(prefix) :]


def backup_database(db_path: str, backup_dir: str = "backups") -> Path:
    """Create a timestamped backup of the SQLite database.

    Uses ``sqlite3.backup()`` for a consistent, online snapshot.
    Returns the path to the backup file.

    Raises
    ------
    FileNotFoundError
        If *db_path* does not exist.
    """
    src_path = Path(db_path)
    if not src_path.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = Path(backup_dir) / f"tcg_market_{timestamp}.db"
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    log.info("backup.start", source=str(src_path), destination=str(backup_path))

    src_conn = sqlite3.connect(db_path)
    try:
        dst_conn = sqlite3.connect(str(backup_path))
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
    finally:
        src_conn.close()

    size_mb = backup_path.stat().st_size / (1024 * 1024)
    log.info("backup.done", path=str(backup_path), size_mb=round(size_mb, 2))

    return backup_path
