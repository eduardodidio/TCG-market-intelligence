# PRD: F09 - Scheduled Price Collection

**Status:** Planned
**Date:** 2026-08-19
**Author:** Eduardo Rutkoski Didio
**Gandalf Decision:** D-20260819-002

## Problem

After F08 enriched the database with multiple sets (240+ cards across 8 sets),
collection remains a manual CLI operation. The developer must remember to run
`python -m src.cli.main update` periodically to keep prices fresh. This has
two consequences:

1. **Data staleness.** If the developer forgets to run the update (or is away
   for a few days), dashboard data becomes stale without any visible signal.
   Users of the dashboard have no way to know whether the prices they see are
   from yesterday or two weeks ago.

2. **No observability.** There is no endpoint or indicator that reports when
   the last collection ran, whether it succeeded, or how many cards have stale
   data. The existing `/health` endpoint only confirms the API process is up,
   not that the data pipeline is healthy.

3. **Unprotected collect endpoints.** The POST endpoints at
   `/api/v1/collect/backfill` and `/api/v1/collect/update` have no
   authentication. Anyone who can reach the API can trigger expensive
   collection operations.

## User Personas

- **Solo developer / operator** -- needs automated, scheduled collection so
  prices stay fresh without manual intervention. Needs a health endpoint to
  verify the pipeline is working.
- **Dashboard consumer** -- needs a visual freshness indicator so they can
  trust that the data they see is recent.

## Goals

1. Provide a health/status endpoint that reports collection pipeline health
2. Protect collect endpoints with a simple API key guard
3. Provide a versionable cron trigger script that automates collection
4. Show data freshness on the frontend Dashboard
5. Document the setup for both Linux/Mac (crontab) and Windows (Task Scheduler)

## Functional Requirements

| ID    | Requirement |
|-------|-------------|
| FR-01 | GET `/api/v1/collect/health` returns: last collection timestamp, next expected run time, total cards count, stale cards count (no observation in last 14 days), recent error count |
| FR-02 | POST `/api/v1/collect/backfill` and POST `/api/v1/collect/update` require a valid API key via `X-API-Key` header |
| FR-03 | API key is read from the `TCG_API_KEY` environment variable; if unset, collect endpoints are unprotected (development convenience) |
| FR-04 | A shell script `scripts/cron_update.sh` calls the update endpoint with the API key, logs the response, and exits with a meaningful exit code |
| FR-05 | Dashboard displays a "Last updated: X ago" freshness indicator using data from the health endpoint |

## Non-Functional Requirements

| ID     | Requirement |
|--------|-------------|
| NFR-01 | Health endpoint responds in < 500ms for databases up to 10k observations |
| NFR-02 | API key guard adds negligible latency (< 1ms) to collect requests |
| NFR-03 | Cron script is POSIX-compliant (bash, curl, jq optional) |
| NFR-04 | No new Python dependencies introduced |
| NFR-05 | Frontend freshness indicator degrades gracefully if health endpoint is unreachable |

## Out of Scope

- In-process scheduler (APScheduler or similar) -- defer until deployment
  story requires it
- Alerting/notification system for failed collections
- GitHub Actions scheduled workflow -- document as future option only
- Rate limiting on collect endpoints beyond the API key guard
- Changes to collection logic itself (backfill, update, retry)

## Acceptance Criteria

1. **AC1:** `curl localhost:8000/api/v1/collect/health` returns JSON with
   `last_collection_at`, `stale_cards_count`, and `recent_errors_count`
2. **AC2:** `curl -X POST localhost:8000/api/v1/collect/update` returns 401
   when `TCG_API_KEY` is set but no `X-API-Key` header is provided
3. **AC3:** `curl -X POST -H "X-API-Key: $TCG_API_KEY" localhost:8000/api/v1/collect/update`
   succeeds with 200
4. **AC4:** `scripts/cron_update.sh` exists, is executable, and exits 0 on
   success / non-zero on failure
5. **AC5:** Dashboard shows "Last updated: X ago" text derived from the health
   endpoint
6. **AC6:** All new code has tests; existing tests still pass
7. **AC7:** Diagrams and README updated
