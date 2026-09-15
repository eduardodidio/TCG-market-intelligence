# F102 -- Auth Hardening

**Status:** planned
**Priority:** P3
**Estimate:** 7 tasks across 3 waves

## Summary

Harden authentication layer with three improvements: (1) admin-driven
password reset flow via CLI + API, (2) OpenAPI documentation with proper
tags/descriptions on all 94+ endpoints, (3) standardized machine-readable
error codes across the entire API surface.

## Scope Decisions

- **No email service.** Password reset is admin-initiated via CLI command
  (`tcg reset-password --email <email>`) which sets a temporary password
  with forced-change flag. No SMTP integration, no reset tokens table.
- **Error codes are additive.** The existing `ErrorDetail(code, message,
  field)` envelope is preserved. We replace generic `HTTP_4xx` codes with
  domain-specific constants (e.g., `AUTH_INVALID_CREDENTIALS`) while
  keeping the response shape identical -- fully backwards compatible.
- **OpenAPI enhancement** is limited to adding `summary`, `description`,
  and `response` declarations on existing router functions, plus a global
  API description. No new endpoints.

## Wave Plan

### Wave 0 -- Foundation (3 tasks, parallel)

| Task | File | Description |
|------|------|-------------|
| T01 | `T01-error-codes.md` | Define `src/api/error_codes.py` constants module |
| T02 | `T02-reset-password-cli.md` | CLI `reset-password` command (sets temp password + expiry) |
| T03 | `T03-openapi-metadata.md` | FastAPI app metadata + tag descriptions |

- T01 creates the error code constants that T04 (Wave 1) will use.
- T02 only touches CLI + repository; independent of API changes.
- T03 only touches `app.py` metadata and tag descriptions; no router edits.

### Wave 1 -- Backend Integration (2 tasks, parallel)

| Task | File | Description |
|------|------|-------------|
| T04 | `T04-apply-error-codes.md` | Replace string literals in routers with error code constants |
| T05 | `T05-openapi-endpoints.md` | Add summaries/descriptions/responses to all router endpoints |

- T04 depends on T01 (error code constants).
- T05 depends on T03 (tag metadata defined). T04 and T05 touch different
  aspects of the router files (exception `detail` vs docstrings/decorators)
  so they can run in parallel without conflicts.

### Wave 2 -- Frontend (2 tasks, parallel)

| Task | File | Description |
|------|------|-------------|
| T06 | `T06-frontend-error-codes.md` | Frontend error code mapping + user-friendly messages |
| T07 | `T07-forgot-password-page.md` | Admin-facing "Reset Password" UI on admin page |

- T06 depends on T04 (error codes applied to API).
- T07 depends on T02 (CLI reset-password exists; the admin API endpoint
  for resetting passwords is added in this task).

## Architecture Notes

### Error Code Design

```python
# src/api/error_codes.py
class ErrorCode:
    # Auth
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
    AUTH_ACCOUNT_INACTIVE = "AUTH_ACCOUNT_INACTIVE"
    AUTH_EMAIL_TAKEN = "AUTH_EMAIL_TAKEN"
    AUTH_PASSWORD_EXPIRED = "AUTH_PASSWORD_EXPIRED"
    AUTH_PASSWORD_MISMATCH = "AUTH_PASSWORD_MISMATCH"

    # Authorization
    AUTHZ_ADMIN_REQUIRED = "AUTHZ_ADMIN_REQUIRED"
    AUTHZ_FORBIDDEN = "AUTHZ_FORBIDDEN"

    # Credits
    CREDIT_INSUFFICIENT = "CREDIT_INSUFFICIENT"

    # Resources
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"

    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"

    # External services
    EXTERNAL_TIMEOUT = "EXTERNAL_TIMEOUT"
    EXTERNAL_FAILURE = "EXTERNAL_FAILURE"

    # Server
    INTERNAL_ERROR = "INTERNAL_ERROR"
```

### Password Reset Flow

```
Admin runs: tcg reset-password --email user@example.com
  -> generates random 12-char temp password
  -> hashes it, updates user.password_hash + password_expires_at (now + 24h)
  -> prints temp password to stdout

User logs in with temp password:
  -> login endpoint detects password_expires_at <= now
  -> returns { password_expired: true, access_token: <5min token> }
  -> frontend redirects to /change-password
  -> user sets new password, gets fresh tokens
```

This flow already exists partially (the login endpoint checks
`password_expires_at` and returns `password_expired: true`). We only need
the CLI command to trigger it and an admin API endpoint.

### OpenAPI Enhancements

- `create_app()` gains `description`, `contact`, `license_info` fields.
- Each tag gets a `description` via `openapi_tags` list.
- Every endpoint gets a proper `summary` (short) and `description`
  (longer) in its decorator or docstring.
- Common error responses declared via `responses` parameter.

## Files Affected (estimated)

### New files
- `src/api/error_codes.py`
- `frontend/src/utils/errorCodes.ts`
- `tests/api/test_error_codes.py`
- `tests/cli/test_reset_password.py`
- `frontend/src/pages/__tests__/AdminResetPassword.test.tsx`

### Modified files
- `src/api/app.py` -- OpenAPI metadata, tag descriptions
- `src/api/deps.py` -- use error code constants
- `src/api/routers/auth.py` -- error codes + reset-password admin endpoint
- `src/api/routers/admin.py` -- error codes + reset-password endpoint
- `src/api/routers/*.py` (all 21 routers) -- error codes, summaries, descriptions
- `src/cli/main.py` -- reset-password command
- `frontend/src/contexts/AuthContext.tsx` -- error code handling
- `frontend/src/pages/AdminPage.tsx` -- reset password section
- `frontend/src/i18n/locales/en.json` -- error messages
- `frontend/src/i18n/locales/pt-BR.json` -- error messages

## Risk Assessment

- **Low risk:** Error codes are additive; old `detail` strings stay as
  `message` field. Frontend currently reads `errors[0].message` which
  keeps working.
- **Low risk:** Password reset reuses existing `password_expires_at`
  mechanism. No new DB tables.
- **No new dependencies.**
