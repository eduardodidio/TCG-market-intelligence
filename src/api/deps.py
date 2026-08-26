from __future__ import annotations

import os
from collections.abc import Generator

from fastapi import Depends, Header, HTTPException

from src.config import get_db_url
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
    db_url = get_db_url()
    repo = Repository(db_url=db_url)
    yield repo


def get_currency_converter_dep():  # noqa: F811
    """FastAPI dependency that yields a CurrencyConverter."""
    from src.services.currency import CurrencyConverter

    db_url = get_db_url()
    repo = Repository(db_url=db_url)
    yield CurrencyConverter(repo)


def get_market_data_service():
    """FastAPI dependency for the singleton MarketDataService."""
    return _create_market_data_service()


def _create_market_data_service():
    """Create (or return cached) singleton MarketDataService.

    Uses a module-level cache to ensure one instance per process.
    """
    if not hasattr(_create_market_data_service, "_instance"):
        from src.services.aggregate_cache import AggregateCache
        from src.services.currency import CurrencyConverter
        from src.services.market_data import MarketDataService

        db_url = get_db_url()
        repo = Repository(db_url=db_url)
        converter = CurrencyConverter(repo)
        cache = AggregateCache()
        _create_market_data_service._instance = MarketDataService(repo, converter, cache)
    return _create_market_data_service._instance


def get_provider_registry():
    """FastAPI dependency for the ProviderRegistry singleton.

    Returns a ProviderRegistry configured from the ``TCG_PROVIDER_ORDER``
    environment variable (default: ``liga,myp``).  If LigaMagic is not
    available (e.g. Playwright not installed), it is silently skipped.
    """
    if not hasattr(get_provider_registry, "_instance"):
        from src.providers.registry import create_registry_from_env

        get_provider_registry._instance = create_registry_from_env()
    return get_provider_registry._instance


def get_credit_service(repo: Repository = Depends(get_db)):
    """FastAPI dependency that yields a CreditService."""
    from src.credits.service import CreditService

    return CreditService(repo)


# Re-export auth dependencies for convenience
from src.auth.dependencies import (  # noqa: E402, F401
    get_current_user,
    get_current_user_id,
    get_optional_user,
    require_auth_or_api_key,
)
from src.domain.models import User  # noqa: E402


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require the current user to be an admin. Raises 403 if not."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
