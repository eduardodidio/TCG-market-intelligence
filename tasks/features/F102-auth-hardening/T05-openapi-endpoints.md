# T05 -- OpenAPI Endpoint Documentation

**Wave:** 1
**Depends on:** T03 (app-level metadata and tags)
**Estimated effort:** medium

## User Story

As a developer integrating with the TEDHC Market API, I want every
endpoint in `/docs` to have a clear summary, description, and documented
error responses so that I can understand what each endpoint does without
reading source code.

## What to Build

Add `summary`, `description`, and `responses` metadata to every endpoint
across all 21 routers. This is a documentation-only change -- no behavior
modifications.

### Pattern

For each endpoint, update the decorator and/or docstring:

```python
@router.post(
    "/login",
    summary="Authenticate with email and password",
    responses={
        401: {"description": "Invalid credentials or inactive account"},
    },
)
def login(body: LoginRequest, response: Response, repo=Depends(get_db)):
    """Authenticate a user with email and password.

    Returns JWT access and refresh tokens. If the user's password is
    expired (admin-reset), returns `password_expired: true` with a
    short-lived token for the change-password flow.
    """
```

### Router-by-router plan

Work through each router file and add:

1. **summary** on the decorator -- short (under 60 chars), imperative
   mood ("List cards", "Create deck", not "Lists cards").
2. **description** in the docstring -- 1-3 sentences explaining behavior,
   edge cases, or auth requirements.
3. **responses** dict on the decorator for common error codes (401, 403,
   404, 422) where applicable.

### Priority routers (most used, least documented)

1. `auth.py` -- 8 endpoints
2. `collection.py` -- ~15 endpoints
3. `cards.py` -- ~8 endpoints
4. `card_search.py` -- ~4 endpoints
5. `credits.py` -- ~5 endpoints
6. `admin.py` -- ~6 endpoints
7. All remaining routers

### Response model documentation

Where response_model is already set, ensure it matches. Where missing,
add `response_model=ApiResponse[X]` if the schema exists.

## Dev Notes

- This task touches docstrings and decorator parameters ONLY. Do NOT
  change any function logic or error handling (that is T04).
- If T04 is running in parallel, coordinate: T04 changes `detail` args
  in `raise HTTPException(...)`, T05 changes `summary`/docstrings/
  `responses` in the decorator. These are different parts of the same
  functions but different code locations, so conflicts should be minimal.
- Use FastAPI's convention: `summary` is the short one-liner shown in the
  endpoint list, the docstring becomes the expanded description.
- For `responses`, use the format:
  ```python
  responses={
      401: {"description": "Authentication required"},
      404: {"description": "Resource not found"},
  }
  ```

## Testing

1. Test that `GET /openapi.json` has `summary` for every path operation.
2. Test that no endpoint has an empty/missing description.
3. Test a sample of endpoints have `responses` keys for expected error
   codes.
4. Spot-check that `/docs` renders without JavaScript errors (manual
   verification during review).

Expected: ~5-6 tests (mostly schema introspection).
