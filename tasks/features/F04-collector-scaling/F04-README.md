# F04 — Collector Scaling: Batch Upsert, Concurrency, Integration Tests

**Status:** done
**Created:** 2026-08-18

## Goal

Prepare the collector pipeline to scale from 30 cards (DMR) to the full
MYP catalog (~10k+ cards). This requires: (1) batch upsert to eliminate
per-row SELECT during price observation inserts, (2) concurrent card
processing with resume capability, and (3) integration tests covering
the collector orchestration layer which currently has zero test coverage.

These items were identified as ACT-06, ACT-07, ACT-08 in the Gandalf
retroactive review (D-20260818-001) and are prerequisites before scaling
to all sets.

## Architecture Impact

- **`src/database/repository.py`** — replace `insert_price_observations`
  with batch `INSERT ... ON CONFLICT DO NOTHING` via SQLAlchemy
- **`src/database/models.py`** — no changes (unique constraint already exists)
- **`src/collectors/backfill.py`** — add `asyncio.Semaphore` concurrency,
  checkpoint/resume via DB state, progress callback
- **`src/providers/myp/provider.py`** — no structural changes (already async)
- **New** `tests/integration/` — integration tests with mocked HTTP for
  full collector pipeline

## Global Acceptance Criteria

1. **AC1** `insert_price_observations` uses batch INSERT ON CONFLICT DO NOTHING
   (no per-row SELECT)
2. **AC2** Backfill processes cards concurrently with configurable concurrency
   limit (default: 3)
3. **AC3** Backfill skips cards already fully collected (resume capability)
4. **AC4** Integration tests cover `run_backfill`, `run_update`, `run_retry_failed`
   with mocked HTTP responses
5. **AC5** All existing 105 unit tests still pass
6. **AC6** Batch upsert returns accurate inserted count
7. **AC7** Progress reporting shows cards completed / total

## Waves

- **Wave 0**: F04-T01  (batch upsert in repository)
- **Wave 1**: F04-T02  (concurrency + resume in backfill)
- **Wave 2**: F04-T03  (integration tests for collector pipeline)

## Diagrams

- Update `docs/diagrams/F01-architecture.mmd` — add concurrency/batch flow
- Update `docs/diagrams/F01-journey.mmd` — reflect resume behavior
