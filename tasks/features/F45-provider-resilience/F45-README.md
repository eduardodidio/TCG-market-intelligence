# F45 Provider Resilience -- Rate-limit re-queue + 404 fast-fail

**Status: planned**

## Problem

MYP Cards has rate-limiting (HTTP 429). When the provider exhausts retries,
the card is permanently skipped in that run. Additionally, 404 errors (dead
product pages) are retried 3x unnecessarily, wasting 3-12 seconds per dead
product. All errors raise generic `RuntimeError` -- callers cannot
distinguish error types.

## Goals

1. Custom exception hierarchy so callers can react differently to 404, 429,
   5xx, and other HTTP errors.
2. Provider `_fetch()` fast-fails on 404 (no retry) and raises typed
   exceptions after exhausting retries.
3. Scan orchestrator re-queues rate-limited cards for a second pass with
   longer delays.
4. Sync orchestrator re-queues rate-limited cards and marks 404s as
   permanently failed.

## Wave Plan

### Wave 1 (sequential dependency)

| Task | Title | Depends on |
|------|-------|------------|
| T01  | Custom exceptions module | -- |
| T02  | Provider `_fetch` refactor | T01 |

T02 depends on T01 because the provider must import and raise the new
exception classes. Both are small and should be reviewed together.

### Wave 2 (parallel)

| Task | Title | Depends on |
|------|-------|------------|
| T03  | Scan re-queue on RateLimitError | T02 |
| T04  | Sync re-queue on RateLimitError + 404 fast-fail | T02 |

T03 and T04 are independent of each other. Both depend on T02 because they
catch the typed exceptions raised by the refactored provider.

## Files Touched

- `src/providers/myp/exceptions.py` (new)
- `src/providers/myp/provider.py`
- `src/collectors/scan.py`
- `src/collectors/sync_collection.py`
- `src/domain/models.py` (SyncSummary new fields)
- `tests/unit/test_provider.py`
- `tests/unit/providers/test_exceptions.py` (new)
- `tests/collectors/test_scan.py`
- `tests/collectors/test_sync_collection.py`
