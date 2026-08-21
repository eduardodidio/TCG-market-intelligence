"""FastAPI auth dependencies for JWT-based authentication."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from jose import JWTError

from src.api.deps import get_db
from src.auth.jwt import decode_token
from src.database.repository import Repository
from src.domain.models import User


def _extract_token(request: Request) -> str | None:
    """Extract JWT from Authorization header or cookie."""
    # Check Authorization header first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]

    # Fall back to cookie
    return request.cookies.get("access_token")


def get_current_user(
    request: Request,
    repo: Repository = Depends(get_db),
) -> User:
    """Extract and validate JWT, returning the authenticated User.

    Raises 401 if no valid token is present.
    """
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user_row = repo.get_user_by_id(int(user_id))
    if user_row is None:
        raise HTTPException(status_code=401, detail="User not found")

    if not user_row.is_active:
        raise HTTPException(status_code=401, detail="User account is inactive")

    return User(
        id=user_row.id,
        email=user_row.email,
        display_name=user_row.display_name,
        avatar_url=user_row.avatar_url,
        auth_provider=user_row.auth_provider,
        preferred_currency=user_row.preferred_currency,
        is_active=bool(user_row.is_active),
    )


def get_optional_user(
    request: Request,
    repo: Repository = Depends(get_db),
) -> User | None:
    """Like get_current_user, but returns None instead of raising 401."""
    token = _extract_token(request)
    if not token:
        return None

    try:
        payload = decode_token(token)
    except JWTError:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    user_row = repo.get_user_by_id(int(user_id))
    if user_row is None or not user_row.is_active:
        return None

    return User(
        id=user_row.id,
        email=user_row.email,
        display_name=user_row.display_name,
        avatar_url=user_row.avatar_url,
        auth_provider=user_row.auth_provider,
        preferred_currency=user_row.preferred_currency,
        is_active=bool(user_row.is_active),
    )


def get_current_user_id(user: User = Depends(get_current_user)) -> str:
    """Return the current user's ID as a string (for collection queries)."""
    return str(user.id)


def require_auth_or_api_key(
    request: Request,
    repo: Repository = Depends(get_db),
) -> str:
    """Accept EITHER a valid JWT (returning user ID) OR a valid API key.

    This allows browser users (JWT) and cron/CLI calls (X-API-Key) to both
    access protected endpoints. If both fail, raises 401.

    When authenticated via API key, returns a fallback user ID. If a real
    user exists in the database, we use their ID; otherwise we return
    "api_key_user" as a sentinel.
    """
    import os

    # Try JWT first
    token = _extract_token(request)
    if token:
        try:
            payload = decode_token(token)
            user_id = payload.get("sub")
            if user_id:
                user_row = repo.get_user_by_id(int(user_id))
                if user_row and user_row.is_active:
                    return str(user_row.id)
        except JWTError:
            pass

    # Fall back to API key
    expected = os.environ.get("TCG_API_KEY")
    api_key = request.headers.get("x-api-key")
    if expected is not None and api_key == expected:
        # API key valid — return first active user or fallback
        return "api_key_user"

    # Dev mode: no TCG_API_KEY set and no JWT → allow through for backwards compat
    if expected is None and not token:
        return "api_key_user"

    raise HTTPException(status_code=401, detail="Authentication required")
