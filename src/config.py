from __future__ import annotations

import os

_DEFAULT_DB_URL = "sqlite:///tcg_market.db"


def get_db_url() -> str:
    """Return the database URL from TCG_DATABASE_URL env var or the default."""
    return os.environ.get("TCG_DATABASE_URL", _DEFAULT_DB_URL)
