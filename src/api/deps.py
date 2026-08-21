from __future__ import annotations

import os
from collections.abc import Generator

from fastapi import Header, HTTPException

from src.database.repository import Repository


def verify_api_key(x_api_key: str | None = Header(None)) -> None:
    """Require X-API-Key header when TCG_API_KEY env var is set.

    When TCG_API_KEY is not configured the guard is a no-op (dev mode).
    """
    expected = os.environ.get("TCG_API_KEY")
    if expected is None:
        return  # No key configured — dev mode
    if x_api_key is None or x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def get_db() -> Generator[Repository, None, None]:
    """FastAPI dependency that yields a Repository instance."""
    db_url = os.environ.get("TCG_DATABASE_URL", "sqlite:///tcg_market.db")
    repo = Repository(db_url=db_url)
    yield repo


def get_currency_converter_dep():  # noqa: F811
    """FastAPI dependency that yields a CurrencyConverter."""
    from src.services.currency import CurrencyConverter

    db_url = os.environ.get("TCG_DATABASE_URL", "sqlite:///tcg_market.db")
    repo = Repository(db_url=db_url)
    yield CurrencyConverter(repo)


# Re-export auth dependencies for convenience
from src.auth.dependencies import (  # noqa: E402, F401
    get_current_user,
    get_current_user_id,
    get_optional_user,
    require_auth_or_api_key,
)
