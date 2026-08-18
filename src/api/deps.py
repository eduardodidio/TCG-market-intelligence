from __future__ import annotations

import os
from collections.abc import Generator

from src.database.repository import Repository


def get_db() -> Generator[Repository, None, None]:
    """FastAPI dependency that yields a Repository instance."""
    db_url = os.environ.get("TCG_DATABASE_URL", "sqlite:///tcg_market.db")
    repo = Repository(db_url=db_url)
    yield repo
