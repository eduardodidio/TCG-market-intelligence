# PRD: F13 - Collection Scans

**Status:** Delivered
**Date:** 2026-08-20
**Author:** Eduardo Rutkoski Didio
**Prerequisite:** F12 (JSON-LD Price Snapshot)

## Problem

The existing price collection workflow relies on ad-hoc CLI commands
(`snapshot-prices`, `sync-collection`) that lack filtering capabilities,
metrics tracking, and an audit trail. Users cannot:

- Scan a subset of their collection (e.g., only a specific set or format)
- Track how many cards were processed, failed, or skipped per run
- Review historical scan executions to detect patterns in failures
- Trigger scans from the frontend with custom filters

This makes it difficult to monitor collection health, debug failures, and
build confidence that prices are being collected reliably.

## Solution

Introduce a unified scan orchestrator that replaces ad-hoc snapshot/sync
commands with a structured, filterable, trackable scan model. Each scan
execution is persisted as a `scan_run` row with full metrics, enabling
auditing and historical analysis.

## Scope

| Component | Change |
|-----------|--------|
| `src/domain/models.py` | New `ScanStatus`, `ScanType`, `ScanFilter`, `ScanRun` models |
| `src/database/models.py` | New `ScanRunRow` table |
| `src/database/repository.py` | CRUD for `scan_runs` + `get_cards_for_scan()` filtered queries |
| `src/collectors/scan.py` | New file -- generic scan orchestrator |
| `src/cli/main.py` | New `scan` and `scan-history` commands |
| `src/api/schemas/scans.py` | New file -- Pydantic request/response schemas |
| `src/api/routers/scans.py` | New file -- scan trigger and history endpoints |
| `frontend/src/pages/Scans.tsx` | New file -- scan management page |
| `frontend/src/components/ScanForm.tsx` | New file -- scan trigger form |
| `frontend/src/components/ScanHistoryTable.tsx` | New file -- history table |
| `frontend/src/hooks/useScans.ts` | New file -- scan API hooks |

## Constraints

- **Collection-only:** scans operate on cards linked to the user's collection
- **No schema changes to existing tables:** new `scan_runs` table only
- **Reuses existing provider:** `MypCardsProvider.fetch_current_price()` from F12
- **No new dependencies:** uses existing `curl_cffi`, `beautifulsoup4`, `structlog`
- **Rate-limited:** respects MYP rate limits via `asyncio.Semaphore` with
  configurable concurrency (default 3) and delay (default 1s)

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-01 | Scan orchestrator accepts a `ScanFilter` with type, set_code, format, rarity, and card_ids fields |
| FR-02 | Each scan run is persisted in `scan_runs` table with id, type, filter JSON, status, timestamps, and card counts |
| FR-03 | Repository provides `get_cards_for_scan()` that filters linked collection entries by the scan filter criteria |
| FR-04 | Scan orchestrator fetches current price via JSON-LD for each matched card and stores observations |
| FR-05 | Per-card errors are isolated -- a single card failure does not abort the entire scan |
| FR-06 | `scan` CLI command triggers a scan with `--type`, `--set`, `--format`, `--rarity`, `--card-ids`, `--limit`, `--dry-run`, `--delay`, `--concurrency` options |
| FR-07 | `scan-history` CLI command lists past scan runs with metrics (total, processed, failed, observations) |
| FR-08 | `POST /api/v1/scans` triggers a background scan with filter parameters |
| FR-09 | `GET /api/v1/scans` lists scan history with pagination |
| FR-10 | `GET /api/v1/scans/{id}` returns scan detail including error summary |
| FR-11 | Frontend Scans page displays a trigger form and a history table |

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-01 | Concurrency controlled via `asyncio.Semaphore` (configurable, default 3) |
| NFR-02 | Per-card errors are logged and do not abort the scan run |
| NFR-03 | Status logic: `completed` if error rate <= 50%, `failed` otherwise |
| NFR-04 | Scan metrics (cards_total, cards_processed, cards_failed, observations_saved) updated in real-time |
| NFR-05 | No new Python or npm dependencies introduced |

## Out of Scope

- Multi-user support (single-user collection model)
- Real-time scan progress via WebSocket
- Scheduled/recurring scans (future feature)
- Alternative price sources beyond MYP JSON-LD
- Price change alerting or notifications

## Success Metrics

| Metric | Target |
|--------|--------|
| Scan completion rate | > 95% of scans reach `completed` status |
| Card error rate | < 5% per scan run |
| Filter accuracy | Filtered scans return only matching cards |
| Audit trail | All scan runs queryable via CLI, API, and frontend |

## Acceptance Criteria

1. Scan runs are persisted in `scan_runs` table with full metrics
2. Scans can filter by collection, set_code, format, rarity, card IDs
3. `scan` CLI triggers a scan with filter options and prints summary
4. `scan-history` CLI lists past scan runs with metrics
5. `POST /api/v1/scans` triggers a background scan
6. `GET /api/v1/scans` lists scan history with pagination
7. `GET /api/v1/scans/{id}` returns scan detail with error summary
8. Frontend Scans page shows history and allows triggering new scans
9. All existing tests pass (715+ backend, 192+ frontend)
10. New tests added for all layers (coverage >= 90%)
11. README.md updated with F13 delivery notes
