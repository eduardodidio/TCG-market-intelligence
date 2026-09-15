# T04 -- Apply Error Codes to All Routers

**Wave:** 1
**Depends on:** T01 (error code constants + api_error helper)
**Estimated effort:** medium

## User Story

As a frontend developer, I want every API error response to include a
specific error code so that I can programmatically distinguish between
"invalid credentials", "token expired", "insufficient credits", and
"not found" without parsing human-readable message strings.

## What to Build

Replace all `raise HTTPException(status_code=N, detail="string")` calls
across every router with `raise api_error(N, ErrorCode.XXX, "string")`.

### Migration Map

Below is the complete mapping of existing error strings to error codes.
The `message` string stays the same for backwards compatibility -- only
the `code` field in the error response changes.

#### auth.py
| Line | Old detail | New code |
|------|-----------|----------|
| 36 | "Email already registered" | `AUTH_EMAIL_TAKEN` |
| 62 | "Invalid credentials" | `AUTH_INVALID_CREDENTIALS` |
| 65 | "Invalid credentials" | `AUTH_INVALID_CREDENTIALS` |
| 68 | "Account is inactive" | `AUTH_ACCOUNT_INACTIVE` |
| 139 | "No preferences provided" | `VALIDATION_EMPTY_UPDATE` |
| 143 | "User not found" | `RESOURCE_NOT_FOUND` |
| 168 | "Password change not available" | `AUTH_PASSWORD_UNAVAILABLE` |
| 171 | "Current password is incorrect" | `AUTH_PASSWORD_MISMATCH` |
| 191 | "Unknown OAuth provider: ..." | `RESOURCE_NOT_FOUND` |
| 194 | "OAuth provider ... not configured" | `AUTH_OAUTH_NOT_CONFIGURED` |
| 220 | "Missing authorization code" | `AUTH_MISSING_AUTH_CODE` |
| 224 | "OAuth callback flow not yet implemented" | `AUTH_OAUTH_NOT_IMPLEMENTED` |
| 241 | "Invalid or expired refresh token" | `AUTH_TOKEN_INVALID` |
| 244 | "Invalid token type" | `AUTH_TOKEN_INVALID` |
| 249 | "User not found or inactive" | `AUTH_ACCOUNT_INACTIVE` |

#### deps.py
| Line | Old detail | New code |
|------|-----------|----------|
| 21 | "Invalid or missing API key" | `AUTHZ_API_KEY_INVALID` |
| 107 | "Admin access required" | `AUTHZ_ADMIN_REQUIRED` |

#### admin.py
| Old detail | New code |
|-----------|----------|
| "Email already registered" | `AUTH_EMAIL_TAKEN` |
| "Cannot delete yourself" | `AUTHZ_FORBIDDEN` |
| "User not found" | `RESOURCE_NOT_FOUND` |
| "Error not found" | `RESOURCE_NOT_FOUND` |

#### card_search.py
| Old detail | New code |
|-----------|----------|
| "Insufficient credits" | `CREDIT_INSUFFICIENT` |
| "Liga search timed out" | `EXTERNAL_TIMEOUT` |
| "Liga search failed" | `EXTERNAL_FAILURE` |
| "MYP search timed out" | `EXTERNAL_TIMEOUT` |
| "MYP search failed" | `EXTERNAL_FAILURE` |
| "No search providers available" | `EXTERNAL_PROVIDER_UNAVAILABLE` |

#### cards.py
| Old detail | New code |
|-----------|----------|
| "card_ids must be comma-separated integers" | `VALIDATION_ERROR` |
| "Maximum 50 card_ids per request" | `VALIDATION_LIMIT_EXCEEDED` |
| "Card not found" | `RESOURCE_NOT_FOUND` |

#### collection.py
| Old detail | New code |
|-----------|----------|
| "No fields to update" | `VALIDATION_EMPTY_UPDATE` |
| "Not your entry" (403) | `AUTHZ_FORBIDDEN` |
| "Entry not found" (404) | `RESOURCE_NOT_FOUND` |

#### All other routers
Apply `RESOURCE_NOT_FOUND` for 404s, `AUTHZ_FORBIDDEN` for 403s,
`VALIDATION_ERROR` for 422s, following the same pattern.

### Also update auth dependencies

In `src/auth/dependencies.py`, update the HTTPException calls in
`get_current_user` (token validation failures) to use:
- `AUTH_TOKEN_INVALID` for missing/malformed tokens
- `AUTH_TOKEN_EXPIRED` for expired tokens (if distinguishable)
- `AUTH_ACCOUNT_INACTIVE` for inactive users

## Dev Notes

- Import `from src.api.error_codes import ErrorCode, api_error` at the
  top of each router.
- Keep the human-readable message string identical to the old `detail`
  value so existing frontend code that reads `errors[0].message` is
  unaffected.
- This is a large but mechanical change. Work through routers
  alphabetically.
- The exception handler in `app.py` (modified by T01) will extract the
  `code` from the dict detail automatically.

## Testing

Create `tests/api/test_error_codes_integration.py`:

1. Test login with wrong password returns `AUTH_INVALID_CREDENTIALS` code.
2. Test register with existing email returns `AUTH_EMAIL_TAKEN` code.
3. Test refresh with invalid token returns `AUTH_TOKEN_INVALID` code.
4. Test accessing admin endpoint as non-admin returns `AUTHZ_ADMIN_REQUIRED`.
5. Test card not found returns `RESOURCE_NOT_FOUND`.
6. Test that all error responses still have `errors[0].message` populated
   (backwards compatibility).
7. Test that `errors[0].code` is no longer `HTTP_4xx` for migrated
   endpoints.

Expected: ~12-15 tests.
