# F13 -- Buscas por Colecao (Overview)

## Problem

The system currently has separate, hardcoded scan pipelines (`backfill`,
`sync-collection`, `snapshot-prices`) that operate on fixed targets (all
editions, all collection cards, all linked cards). There is no unified way
to:

1. Scan a subset of cards (by set, format, rarity, or custom list)
2. Track scan executions with metrics (start, end, status, processed, errors)
3. View scan history to understand data freshness and error patterns

The user needs independent, filterable scans with full execution tracking
so they can answer: "when was this set last scanned?", "which scans failed?",
"how fresh is my collection data?"

## Scope

- New `scan_runs` DB table to persist execution history
- Domain models: `ScanRun`, `ScanFilter`, `ScanStatus`
- Generic scan orchestrator that accepts filters and delegates to existing
  price-fetching logic
- CLI commands: `scan` (trigger) and `scan-history` (list past runs)
- API endpoints: `POST /api/v1/scans`, `GET /api/v1/scans`, `GET /api/v1/scans/{id}`
- Frontend: Scans page with trigger form, history table, run details
- Reuses existing `snapshot_prices` fetching logic (JSON-LD)

## Constraints

- No new Python dependencies
- No new npm dependencies
- Reuse existing `MypCardsProvider.fetch_current_price()` for price fetching
- Reuse existing `Repository.insert_price_observations()` for storage
- Rate limiting via existing `asyncio.Semaphore` pattern
- Single-user (no multi-tenancy changes)

## Acceptance Criteria (titles)

- AC-1: Scan runs are persisted with start/end timestamps and status
- AC-2: Scans can filter by collection, set_code, format, rarity, card IDs
- AC-3: `scan` CLI triggers a scan with filter options and prints summary
- AC-4: `scan-history` CLI lists past scan runs with metrics
- AC-5: API endpoints for trigger, list, and detail of scan runs
- AC-6: Frontend Scans page shows history and allows triggering new scans
- AC-7: Existing tests pass, new tests added (coverage >= 90%)
- AC-8: Diagrams and README updated
