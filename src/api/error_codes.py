"""Standardized API error codes for machine-readable error responses.

Every HTTPException raised by the API should use one of these codes via
the ``api_error()`` helper.  The global exception handler in ``app.py``
extracts the code from the detail dict and returns it in the standard
``ErrorDetail`` envelope.

This module is intentionally flat (no enums, no inheritance) so that
error codes are simple string constants suitable for serialization and
comparison both in Python and in frontend TypeScript.
"""

from __future__ import annotations

from fastapi import HTTPException


class ErrorCode:
    """Machine-readable error code constants."""

    # Authentication
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
    AUTH_ACCOUNT_INACTIVE = "AUTH_ACCOUNT_INACTIVE"
    AUTH_EMAIL_TAKEN = "AUTH_EMAIL_TAKEN"
    AUTH_PASSWORD_EXPIRED = "AUTH_PASSWORD_EXPIRED"
    AUTH_PASSWORD_MISMATCH = "AUTH_PASSWORD_MISMATCH"
    AUTH_PASSWORD_UNAVAILABLE = "AUTH_PASSWORD_UNAVAILABLE"
    AUTH_OAUTH_NOT_CONFIGURED = "AUTH_OAUTH_NOT_CONFIGURED"
    AUTH_OAUTH_NOT_IMPLEMENTED = "AUTH_OAUTH_NOT_IMPLEMENTED"
    AUTH_MISSING_AUTH_CODE = "AUTH_MISSING_AUTH_CODE"

    # Authorization
    AUTHZ_ADMIN_REQUIRED = "AUTHZ_ADMIN_REQUIRED"
    AUTHZ_FORBIDDEN = "AUTHZ_FORBIDDEN"
    AUTHZ_API_KEY_INVALID = "AUTHZ_API_KEY_INVALID"

    # Credits
    CREDIT_INSUFFICIENT = "CREDIT_INSUFFICIENT"

    # Resources
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    RESOURCE_GONE = "RESOURCE_GONE"

    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    VALIDATION_EMPTY_UPDATE = "VALIDATION_EMPTY_UPDATE"
    VALIDATION_LIMIT_EXCEEDED = "VALIDATION_LIMIT_EXCEEDED"

    # External services
    EXTERNAL_TIMEOUT = "EXTERNAL_TIMEOUT"
    EXTERNAL_FAILURE = "EXTERNAL_FAILURE"
    EXTERNAL_PROVIDER_UNAVAILABLE = "EXTERNAL_PROVIDER_UNAVAILABLE"

    # Server
    INTERNAL_ERROR = "INTERNAL_ERROR"


def api_error(
    status_code: int,
    code: str,
    message: str,
    field: str | None = None,
) -> HTTPException:
    """Create an HTTPException with a structured error code in the detail.

    The global exception handler in ``app.py`` detects dict-shaped details
    and extracts the ``code`` key, producing a proper ``ErrorDetail``
    envelope.  This helper is syntactic sugar -- routers may also raise
    ``HTTPException(detail={"code": ..., "message": ...})`` directly.
    """
    detail: dict = {"code": code, "message": message}
    if field is not None:
        detail["field"] = field
    return HTTPException(status_code=status_code, detail=detail)
