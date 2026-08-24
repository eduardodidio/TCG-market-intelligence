"""JWT token creation and validation."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours
_REFRESH_TOKEN_EXPIRE_DAYS = 30  # 30 days


def _get_secret() -> str:
    secret = os.environ.get("TCG_JWT_SECRET")
    if not secret:
        raise RuntimeError(
            "TCG_JWT_SECRET environment variable is required. "
            "Set it before starting the application."
        )
    return secret


def create_access_token(user_id: int, email: str) -> str:
    """Create a JWT access token (24 hours)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "type": "access",
        "exp": now + timedelta(minutes=_ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": now,
    }
    return jwt.encode(payload, _get_secret(), algorithm=_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """Create a long-lived JWT refresh token (30 days)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": now + timedelta(days=_REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": now,
    }
    return jwt.encode(payload, _get_secret(), algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises JWTError on failure."""
    try:
        return jwt.decode(token, _get_secret(), algorithms=[_ALGORITHM])
    except JWTError:
        raise
