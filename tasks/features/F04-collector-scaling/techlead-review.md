# TechLead Review -- F04 Collector Scaling

**Reviewer:** TechLead agent
**Date:** 2026-08-18
**Feature:** F04 -- Collector Scaling: Batch Upsert, Concurrency, Integration Tests
**Verdict:** APPROVED (with 1 minor fix required before merge)

---

## Summary

F04 delivers all three planned capabilities: batch upsert via SQLite's
`INSERT ... ON CONFLICT DO NOTHING` (T01), concurrent card processing with
`asyncio.Semaphore` plus DB-based resume (T02), and 10 integration tests
covering the full collector pipeline with mocked HTTP (T03). The implementation
is clean, well-structured, and respects the existing architecture layers.

Test count grew from 105 to 131 (26 new tests). All 131 pass. The integration
test suite completes in under 2 seconds. The full suite runs in ~7 seconds.

---

## AC Coverage

| AC  | Description                                | Status | Evidence |
|-----|--------------------------------------------|--------|----------|
| AC1 | Batch INSERT ON CONFLICT DO NOTHING        | PASS   | `repository.py:103-114` uses `sqlite_insert().on_conflict_do_nothing()` -- no per-row SELECT |
| AC2 | Configurable concurrency (default 3)       | PASS   | `backfill.py:72` creates `Semaphore(concurrency)`, default=3 in signature |
| AC3 | Resume: skip already-collected cards       | PASS   | `backfill.py:60-68` queries DB for collected IDs, filters discovered list |
| AC4 | Integration tests for backfill/update/retry | PASS  | 10 integration tests in `test_collector_pipeline.py` |
| AC5 | All 105 original tests still pass          | PASS   | 131 total tests pass (105 original + 26 new) |
| AC6 | Batch upsert returns accurate count        | PASS   | Tests verify: 10 new->10, 10 dupes->0, mixed 15 with 10 overlap->5, 600 large batch->600 |
| AC7 | Progress reporting (cards completed/total) | PASS   | `backfill.py:77-82` logs `processing_card` with index/total; verified by `TestProgressLogging` |

---

## Issues Found

### MINOR-01: Unused import in integration tests (lint error)

**File:** `tests/integration/test_collector_pipeline.py`, line 17
**Issue:** `from src.database.models import Base` is imported but never used.
**Impact:** Fails `ruff check`. Blocks clean lint status.
**Fix:** Remove the unused import.

### NIT-01: Batch upsert is per-row, not truly batched

**File:** `src/database/repository.py`, lines 102-117
**Observation:** Despite the chunking loop (batches of 500), each row within a
chunk is still inserted individually via `session.execute(stmt)`. This is a
single-row `INSERT ... ON CONFLICT DO NOTHING` per iteration, not a multi-row
`INSERT ... VALUES (...), (...), ...`. The entire chunk runs within one
transaction (commit at line 118), so transactional overhead is fine, but the
per-row execute means N round-trips to SQLite per chunk.

**Impact:** For the current scale (~10k cards x 150 obs = 1.5M rows), this is
adequate. SQLite is in-process so "round-trips" are just function calls. At
10M+ rows, a true multi-row insert (passing a list of dicts to `.values()`)
would be measurably faster. This is not blocking for F04's goals.

**Recommendation:** Log this as a future optimization. If backfill timing
becomes a bottleneck after scaling to all sets, refactor to multi-row insert
and use count-before/count-after for the inserted count (since `rowcount` for
multi-row ON CONFLICT DO NOTHING may not return per-row granularity).

### NIT-02: `run_update` and `run_retry_failed` remain sequential

**File:** `src/collectors/backfill.py`, lines 164-278
**Observation:** The task spec (F04-T02) explicitly states these remain
sequential, so this is by design. Noting for completeness: when the catalog
scales, `run_update` processing hundreds of cards sequentially may become the
next bottleneck.

### NIT-03: Integration test concurrency assertion is weak

**File:** `tests/integration/test_collector_pipeline.py`, lines 437-489
**Observation:** `TestBackfillConcurrent` sets up a tracking fetch but the
final assertion only checks `summary.cards_processed == 3` twice. The
`max_concurrent` variable is computed but never asserted against. The unit test
in `test_backfill.py:TestConcurrencyLimit` covers the semaphore limit properly,
so this is not a gap in coverage, but the integration test could be strengthened
by asserting `max_concurrent <= concurrency_limit`.

### INFO-01: Saruman Wave 0 hygiene items not addressed

**Source:** Decision D-20260818-002, rationale field
**Context:** The decision rationale states "ACT-01 through ACT-05, ACT-09,
ACT-10 should ride along as Wave 0 hygiene since they are trivial."
**Status:** These items were NOT included in the F04 task manifest and were not
implemented. The Architect scoped F04 to ACT-06/07/08 only.
**Impact:** These remain as untracked debt. They are minor items (from the
Gandalf review) but should be logged for the next feature's Wave 0 or as a
standalone cleanup PR.
**Recommendation:** Create a tracking issue or add these to the backlog before
F05 planning.

---

## Architecture Review

**Clean architecture:** Respected. The batch upsert change is confined to the
repository layer. Concurrency logic lives in the collector orchestration layer.
The domain models are untouched. The CLI simply passes through new parameters.

**Separation of concerns:** Good. `_process_card` handles single-card logic.
`process_with_sem` wraps it with semaphore + error handling. The resume filter
runs before the concurrent phase.

**Error isolation:** Well implemented. Each card processes in its own
try/except inside the semaphore wrapper. Failed cards are recorded with
`CollectionError` objects and persisted to the DB. The `asyncio.Lock` protects
summary counter mutations.

**Concurrency safety:** The use of `asyncio.Lock` for summary updates is
correct for single-threaded async (asyncio is cooperative, so the lock prevents
interleaving at await points). Since `Repository` methods are synchronous and
SQLite is in-process, there are no thread-safety concerns with the current
architecture.

---

## Diagrams Review

**`docs/diagrams/F01-architecture.mmd`:** Updated to show the concurrent
processing subgraph (Semaphore, gather, process_with_sem), the resume check
decision node, and the new CLI flags (--concurrency, --no-resume). Accurately
reflects the implementation.

**`docs/diagrams/F01-journey.mmd`:** Updated with the resume decision flow
(query DB -> filter -> log skip), the concurrent processing phase with
semaphore acquire/release, and error handling branches. Accurate and complete.

---

## Test Quality

**Unit tests (T01 -- batch upsert):** 6 new test scenarios added to
`test_repository.py`. Cover happy path (10 new), duplicates (returns 0), mixed
(returns 5), empty list (returns 0), large batch crossing chunk boundary (600),
and single observation. All use real SQLite. Thorough.

**Unit tests (T02 -- concurrency/resume):** 11 new tests in `test_backfill.py`
across 7 test classes. Cover resume skip, no-resume, concurrency limit
(instrumented, not timing-based), error isolation (single and multiple
failures), empty discovery, dry-run + resume interaction, summary accuracy with
combined resume + failures, finished_at, and progress logging. Well-structured
mocking with proper isolation.

**Integration tests (T03):** 10 tests in `test_collector_pipeline.py`. Cover
full pipeline, set filter, dry run, resume skip, error continuation,
update, retry-failed, retry with no errors, concurrent execution, and summary
accuracy. Mock only at the HTTP layer (`_fetch`), exercising real parsers, real
repository, and real SQLite. HTML fixtures are minimal but structurally valid.

**Test plan coverage:** All 23 scenarios from `F04-test-plan.md` are addressed
(22 implemented as tests + 1 regression = running the full suite).

---

## Verdict

**APPROVED** -- pending MINOR-01 fix (remove unused `Base` import in
integration tests). All ACs are met, tests are comprehensive, architecture is
clean, and diagrams are in sync.

The NITs are informational and do not block approval. INFO-01 (untracked Wave 0
hygiene items) should be addressed during F05 planning.
