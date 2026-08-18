# PRD: F04 - Collector Scaling: Batch Upsert, Concurrency & Integration Tests

**Status:** Delivered
**Date:** 2026-08-18
**Author:** Eduardo Rutkoski Didio

## Problem

The collector pipeline (F01) was validated with 30 cards from the DMR set,
but cannot scale to the full MYP catalog (~10k+ cards) due to three
bottlenecks:

1. **Per-row INSERT** -- `insert_price_observations` performs a SELECT
   before each INSERT to check for duplicates, creating O(n) round-trips
   to the database per card.
2. **No concurrency** -- cards are processed sequentially. With ~1-2s per
   HTTP request and multiple requests per card (page + history), a full
   catalog backfill would take days.
3. **No resume** -- if the process crashes mid-backfill, it restarts from
   scratch with no way to skip already-collected cards.

Additionally, the collector orchestration layer (`src/collectors/backfill.py`)
had zero test coverage, making refactoring risky.

These items were identified as ACT-06, ACT-07, ACT-08 in the Gandalf
retroactive review (D-20260818-001).

## Goals

1. Replace per-row INSERT with batch `INSERT ... ON CONFLICT DO NOTHING`
   via SQLAlchemy for O(1) round-trips per batch
2. Add `asyncio.Semaphore`-based concurrency with configurable limit
   (default: 3 concurrent card fetches)
3. Implement resume capability -- backfill skips cards already fully
   collected by checking DB state
4. Add integration tests covering `run_backfill`, `run_update`, and
   `run_retry_failed` with mocked HTTP responses
5. Batch upsert returns accurate inserted count
6. Progress reporting shows cards completed / total

## Non-Goals (this phase)

- Distributed workers or multi-process architecture
- Queue-based architecture (Celery, RabbitMQ, etc.)
- Rate limiting at the HTTP client level (already handled by provider)
- Database migration to PostgreSQL
- Horizontal scaling across machines

## Technical Analysis

### Batch Upsert

The existing unique constraint on `(card_variant_id, source, observed_at)`
in `price_observations` already supports `ON CONFLICT DO NOTHING`. The
change replaces the Python-side duplicate check (SELECT + conditional INSERT)
with a single bulk INSERT statement, letting SQLite handle deduplication
at the engine level.

### Concurrency Model

`asyncio.Semaphore(n)` gates concurrent card processing within a single
event loop. This is lighter than multiprocessing and sufficient given the
I/O-bound nature of HTTP requests. The provider is already async
(`curl_cffi` with `asyncio`), so no architectural change is needed.

### Resume Capability

Resume works by querying the database for cards that already have
observations and skipping them during backfill. This is stateless --
no checkpoint file or external state required. The `--no-resume` CLI
flag forces a full re-fetch when needed.

## Acceptance Criteria

1. **AC1:** `insert_price_observations` uses batch INSERT ON CONFLICT DO NOTHING
   (no per-row SELECT)
2. **AC2:** Backfill processes cards concurrently with configurable concurrency
   limit (default: 3)
3. **AC3:** Backfill skips cards already fully collected (resume capability)
4. **AC4:** Integration tests cover `run_backfill`, `run_update`,
   `run_retry_failed` with mocked HTTP responses
5. **AC5:** All existing tests still pass (105 at time of delivery)
6. **AC6:** Batch upsert returns accurate inserted count
7. **AC7:** Progress reporting shows cards completed / total
