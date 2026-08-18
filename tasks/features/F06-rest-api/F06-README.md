# F06 — REST API

**Status:** planned
**Created:** 2026-08-18

## Summary

Expose TCG Market Intelligence data through a FastAPI REST API with eight endpoints covering card listing/detail/history, set listing, market movers/stats, and admin collection triggers. The API uses Pydantic v2 for request/response validation, cursor-based pagination for list endpoints, a standard JSON envelope (`{data, meta, errors}`), and runs on Uvicorn. Authentication is explicitly out of scope. The API reuses the existing `Repository` for database access and `indicators.py` for analytics computations.

## Waves

| Wave | Tasks | Description |
|------|-------|-------------|
| 0 | T01, T02 | Infrastructure: deps, project layout, ADR-0002 accepted, Pydantic schemas, response envelope, DB session dependency |
| 1 | T03, T04, T05 | Feature endpoints: Cards (3 endpoints), Sets+Market (3 endpoints), Collection admin (2 endpoints) |
| 2 | T06, T07 | Integration: app factory with error handling + CORS, integration tests + diagrams + docs update |

## Dependencies

New runtime dependencies (pin in `pyproject.toml`):
- `fastapi>=0.115`
- `uvicorn[standard]>=0.30`
- `pydantic>=2.7`

New dev dependencies:
- `httpx>=0.27` (for `TestClient` / async test client)

## Open Questions

1. **Background jobs for collect endpoints**: The API spec says `POST /collect/backfill` returns a "job status with task ID for polling." Since there is no job queue infrastructure yet, Wave 1 will implement these as synchronous-start endpoints that return an immediate acknowledgment and run the collection in a background `asyncio.Task`. A proper job queue (Celery, ARQ, etc.) is deferred to a future feature.
2. **Rate limiting**: The API spec mentions HTTP 429 but no rate-limiting middleware is in scope for F06. The error code is documented but not enforced.
