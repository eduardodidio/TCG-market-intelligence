from __future__ import annotations

import os

_DEFAULT_DB_URL = "sqlite:///tcg_market.db"


def get_db_url() -> str:
    """Return the database URL from TCG_DATABASE_URL env var or the default."""
    return os.environ.get("TCG_DATABASE_URL", _DEFAULT_DB_URL)


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
