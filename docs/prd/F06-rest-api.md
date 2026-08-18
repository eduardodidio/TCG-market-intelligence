# PRD: F06 - REST API

**Status:** Delivered
**Date:** 2026-08-18
**Author:** Eduardo Rutkoski Didio

## Problem

The TCG Market Intelligence system collects and stores pricing data through a
CLI interface only. There is no programmatic way for external consumers
(frontends, mobile apps, third-party integrations) to query cards, price
history, or market analytics. A REST API is needed to expose the existing
data layer over HTTP.

## Goals

1. Expose card catalog with filtering (game, set, name) and cursor pagination
2. Expose individual card detail with linked source cards
3. Expose price history with configurable time periods
4. Expose aggregated market data (stats, top movers/losers)
5. Provide collection triggers (backfill, update) via HTTP
6. Wrap all responses in a consistent envelope (`data`, `meta`, `errors`)
7. Generate OpenAPI documentation automatically

## Non-Goals (this phase)

- Authentication / authorization
- Rate limiting
- Persistent job queue (jobs are in-memory, lost on restart)
- WebSocket or SSE for real-time updates
- Caching layer (Redis, etc.)
- Deployment configuration (Docker, cloud)

## Technical Analysis

### Stack

- **FastAPI** -- async-capable Python web framework with automatic OpenAPI docs
- **Pydantic v2** -- request/response validation with `model_config`
- **Uvicorn** -- ASGI server
- **SQLAlchemy** -- existing ORM, reused via `Repository` dependency

### Architecture

The API follows a layered architecture:

1. **App factory** (`create_app()`) -- configures middleware (CORS, request ID),
   exception handlers, and mounts routers under `/api/v1`
2. **Routers** -- thin HTTP handlers that delegate to `Repository`
3. **Schemas** -- Pydantic models for request validation and response
   serialization
4. **Dependency injection** -- `get_db()` yields a `Repository` instance,
   overridable in tests
5. **Envelope** -- `ApiResponse[T]` generic wrapper with `data`, `meta`
   (cursor, total, request_id), and `errors`

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/cards` | List cards (filter: game, set, name; cursor pagination) |
| GET | `/api/v1/cards/{id}` | Card detail with source cards |
| GET | `/api/v1/cards/{id}/history` | Price history (period: 30d/90d/180d/1y/3y) |
| GET | `/api/v1/sets` | List sets with card counts |
| GET | `/api/v1/market/movers` | Top gainers and losers (period: 7d/30d/90d) |
| GET | `/api/v1/market/stats` | Aggregate market statistics |
| POST | `/api/v1/collect/backfill` | Trigger backfill job |
| POST | `/api/v1/collect/update` | Trigger update job |

### Middleware

- **CORS** -- permissive (`*`) for development; tighten in production
- **Request ID** -- UUID attached to every request/response for tracing
- **Exception handlers** -- validation errors, HTTP errors, and unhandled
  exceptions all return the standard envelope format

## Acceptance Criteria

1. **AC1:** All 8 API endpoints return valid JSON in the envelope format
2. **AC2:** `GET /cards` supports `game`, `set`, `name` query filters
3. **AC3:** Cursor-based pagination works with `limit` and `cursor` params
4. **AC4:** `GET /cards/{id}` returns 404 envelope for missing cards
5. **AC5:** `GET /cards/{id}/history` filters by period parameter
6. **AC6:** `GET /market/movers` identifies gainers and losers correctly
7. **AC7:** `GET /market/stats` returns accurate totals
8. **AC8:** `POST /collect/backfill` and `/update` return job IDs without
   blocking
9. **AC9:** Every response includes `X-Request-ID` header and
   `meta.request_id`
10. **AC10:** Auto-generated OpenAPI docs available at `/docs`
11. **AC11:** Integration tests cover all endpoints with seeded data
12. **AC12:** Architecture and journey diagrams created under `docs/diagrams/`
