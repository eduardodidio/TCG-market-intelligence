from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_DB_URL = "sqlite:///tcg_market.db"


def _load_dotenv() -> None:
    """Load .env file from project root if it exists.

    Does NOT override existing environment variables.
    """
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv()
_RENDER_DB_URL = "sqlite:////data/tcg_market.db"


def get_db_url() -> str:
    """Return the database URL from environment or a smart default.

    Priority:
    1. DATABASE_URL (Neon / standard PG convention)
    2. TCG_DATABASE_URL (legacy)
    3. Auto-detect Render /data dir (SQLite)
    4. Local SQLite default
    """
    for var in ("DATABASE_URL", "TCG_DATABASE_URL"):
        value = os.environ.get(var)
        if value:
            return value
    # Auto-detect Render persistent disk
    if os.path.isdir("/data"):
        return _RENDER_DB_URL
    return _DEFAULT_DB_URL


def get_error_log_dir() -> str:
    """Return the error log directory path."""
    return os.environ.get("TCG_ERROR_LOG_DIR", "logs/errors")


def get_error_max_age_days() -> int:
    """Return max age in days for error log retention."""
    return int(os.environ.get("TCG_ERROR_MAX_AGE_DAYS", "30"))


def get_error_max_entries() -> int:
    """Return max number of error log entries to keep."""
    return int(os.environ.get("TCG_ERROR_MAX_ENTRIES", "10000"))


def is_liga_disabled() -> bool:
    """Return True if Liga provider is disabled via TCG_LIGA_DISABLED env var."""
    return os.environ.get("TCG_LIGA_DISABLED", "0") == "1"
