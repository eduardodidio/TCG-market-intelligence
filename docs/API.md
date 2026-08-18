# API Reference

> **Status: NOT YET IMPLEMENTED**
>
> This document describes the **planned** REST API for TCG Market Intelligence.
> No endpoints exist today. This is a design document that will guide the
> future API feature (Phase 4 in the [Roadmap](ROADMAP.md)).

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

TBD. Initially the API will run without authentication for local use.
A token-based scheme will be added before any public deployment.

## Endpoints

### Cards

#### `GET /cards`

List cards with optional filters.

| Parameter | Type   | Required | Description                        |
|-----------|--------|----------|------------------------------------|
| `game`    | string | no       | Filter by game (e.g. `magic`)      |
| `set`     | string | no       | Filter by set code (e.g. `dmr`)    |
| `name`    | string | no       | Partial match on card name (EN/PT) |
| `cursor`  | string | no       | Pagination cursor                  |
| `limit`   | int    | no       | Page size (default 50, max 200)    |

**Response:** paginated list of card summaries with latest price.

#### `GET /cards/{id}`

Card details including the most recent price observation.

| Parameter | Type | Required | Description       |
|-----------|------|----------|-------------------|
| `id`      | int  | yes      | Internal card ID  |

**Response:** full card object with source metadata and latest price.

#### `GET /cards/{id}/history`

Price history for a single card.

| Parameter | Type   | Required | Description                              |
|-----------|--------|----------|------------------------------------------|
| `id`      | int    | yes      | Internal card ID                         |
| `period`  | string | no       | `30d`, `90d`, `180d`, `1y`, `3y` (default `90d`) |

**Response:** array of price observations ordered by date.

### Sets

#### `GET /sets`

List all collected sets.

| Parameter | Type   | Required | Description       |
|-----------|--------|----------|-------------------|
| `game`    | string | no       | Filter by game    |

**Response:** array of set objects with card count and collection status.

### Market

#### `GET /market/movers`

Top gainers and losers over a given period.

| Parameter | Type   | Required | Description                              |
|-----------|--------|----------|------------------------------------------|
| `period`  | string | no       | `7d`, `30d`, `90d` (default `30d`)       |
| `limit`   | int    | no       | Number of results per direction (default 10) |

**Response:** `{ gainers: [...], losers: [...] }` sorted by percentage change.

#### `GET /market/stats`

Aggregate market statistics.

| Parameter | Type   | Required | Description    |
|-----------|--------|----------|----------------|
| `game`    | string | no       | Filter by game |

**Response:** total cards tracked, total observations, average price, date range.

### Collection (Admin)

#### `POST /collect/backfill`

Trigger a backfill for a specific set.

| Parameter      | Type   | Required | Description                    |
|----------------|--------|----------|--------------------------------|
| `set`          | string | yes      | Set slug (e.g. `dominaria-remastered`) |
| `limit`        | int    | no       | Max cards to process           |
| `history_days` | int    | no       | Days of history (default 1095) |

**Response:** job status with task ID for polling.

#### `POST /collect/update`

Trigger an incremental update for all known cards.

| Parameter | Type | Required | Description                   |
|-----------|------|----------|-------------------------------|
| `set`     | string | no     | Limit update to a specific set |

**Response:** job status with task ID for polling.

## Response Format

All responses use a standard JSON envelope:

```json
{
  "data": { ... },
  "meta": {
    "cursor": "next_page_token",
    "total": 150,
    "request_id": "uuid"
  },
  "errors": []
}
```

## Pagination

List endpoints use **cursor-based pagination**. The response `meta.cursor`
field contains a token to pass as the `cursor` query parameter for the next
page. When `meta.cursor` is `null`, there are no more results.

## Error Codes

Standard HTTP status codes are used:

| Code | Meaning                |
|------|------------------------|
| 200  | Success                |
| 400  | Bad request / invalid parameters |
| 404  | Resource not found     |
| 422  | Validation error       |
| 429  | Rate limited           |
| 500  | Internal server error  |

Error responses include a domain-specific schema:

```json
{
  "data": null,
  "meta": {},
  "errors": [
    {
      "code": "CARD_NOT_FOUND",
      "message": "Card with id 999 does not exist",
      "field": null
    }
  ]
}
```

## Technology

The API will be built with [FastAPI](https://fastapi.tiangolo.com/) (see
[ADR-0002](adr/0002-web-stack-decision.md) -- planned). FastAPI provides
automatic OpenAPI docs at `/docs` and `/redoc`.
