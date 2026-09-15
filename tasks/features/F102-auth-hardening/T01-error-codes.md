# T01 -- Error Code Constants

**Wave:** 0
**Depends on:** none
**Estimated effort:** small

## User Story

As a frontend developer, I want machine-readable error codes from the API
so that I can display context-specific error messages and handle specific
failure modes programmatically (e.g., redirect on token expiry, show
"insufficient credits" differently from "not found").

## What to Build

Create `src/api/error_codes.py` with a single `ErrorCode` class containing
string constants for every error condition in the codebase.

### Error Code Constants

```python
class ErrorCode:
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
```

Also add a helper function:

```python
from fastapi import HTTPException
from src.api.schemas.envelope import ErrorDetail

def api_error(status_code: int, code: str, message: str, field: str | None = None) -> HTTPException:
    """Create an HTTPException with a structured error code in the detail.

    The global exception handler in app.py will convert this to the
    standard envelope format. The `code` is stored in the detail dict
    so the handler can extract it.
    """
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message, "field": field},
    )
```

Update the `http_exception_handler` in `src/api/app.py` to check if
`exc.detail` is a dict with a `code` key, and use it instead of the
generic `HTTP_{status}` code:

```python
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        error = ErrorDetail(
            code=exc.detail["code"],
            message=exc.detail.get("message", str(exc.detail)),
            field=exc.detail.get("field"),
        )
    else:
        error = ErrorDetail(
            code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
        )
    # ... rest unchanged
```

This approach is backwards compatible: existing `raise HTTPException(...,
detail="string")` calls continue to produce `HTTP_4xx` codes until T04
migrates them.

## Dev Notes

- Keep the class flat (no inheritance, no enums). String constants are
  simplest for serialization and comparison.
- The `api_error()` helper is optional sugar -- routers can also raise
  `HTTPException(detail={"code": ..., "message": ...})` directly.
- Do NOT modify any router files in this task. That is T04.

## Testing

Create `tests/api/test_error_codes.py`:

1. Test that all error codes are unique strings.
2. Test that `api_error()` returns an HTTPException with the correct
   status code and structured detail.
3. Test the updated `http_exception_handler` handles both dict and string
   detail formats correctly (use test client).
4. Test that the existing string-based HTTPExceptions still produce valid
   error responses (backwards compatibility).

Expected: ~8-10 tests.
