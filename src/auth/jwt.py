"""JWT token creation and validation."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_MINUTES = 30
_REFRESH_TOKEN_EXPIRE_DAYS = 7

# Fallback to a random secret for dev; production MUST set TCG_JWT_SECRET.
_dev_secret: str | None = None


def _get_secret() -> str:
    global _dev_secret
    secret = os.environ.get("TCG_JWT_SECRET")
    if secret:
        return secret
    if _dev_secret is None:
        _dev_secret = str(uuid.uuid4())
    return _dev_secret


def create_access_token(user_id: int, email: str) -> str:
    """Create a short-lived JWT access token (30 min)."""
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
    """Create a long-lived JWT refresh token (7 days)."""
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
