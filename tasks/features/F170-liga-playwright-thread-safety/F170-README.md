# F170 -- Liga Playwright Thread Safety (Windows greenlet fix)

**Status:** planned

## User Story

As a user running liga_sweep on Windows, I want the Playwright browser
operations to always execute on the same thread, so that sweeps complete
without intermittent "Cannot switch to a different thread" greenlet errors
and cascading "Sync page not available" failures.

## Problem

On Windows, `LigaMagicProvider` dispatches each sync Playwright call via
`asyncio.to_thread()`, which uses the **default** `ThreadPoolExecutor`.
The default executor does NOT guarantee the same OS thread across calls.
Playwright's sync API binds to the thread where `sync_playwright().start()`
was called, so when a subsequent call lands on a different thread, greenlet
raises:

```
Cannot switch to a different thread
Current: <greenlet ...>  Expected: <greenlet ...>
```

After this error triggers `_reset_browser_sync()`, the page is destroyed
(`_sync_page = None`) but never re-opened, causing every subsequent call to
fail with "Sync page not available" for the rest of the sweep.

## Fix Strategy

Replace all `asyncio.to_thread()` calls with
`loop.run_in_executor(self._executor, ...)` using a **dedicated
single-thread executor** (`ThreadPoolExecutor(max_workers=1)`). This
guarantees every Playwright operation runs on the same OS thread.

Additionally, after `_reset_browser_sync()` destroys the browser, call
`_open_sync()` immediately to restore the page so the sweep can continue.

## Wave Breakdown

### Wave 0 -- Single-thread executor + browser recovery (1 task)

| Task | Description |
|------|-------------|
| T01  | Replace `asyncio.to_thread` with dedicated executor; add recovery after reset |

### Wave 1 -- Tests (1 task)

| Task | Description |
|------|-------------|
| T02  | Unit tests for thread-safety guarantee and browser recovery |

## Acceptance Criteria

1. `LigaMagicProvider.__init__` creates a `ThreadPoolExecutor(max_workers=1)`.
2. ALL `asyncio.to_thread()` calls in `provider.py` are replaced with
   `loop.run_in_executor(self._executor, ...)`.
3. `close()` shuts down the executor (`self._executor.shutdown(wait=False)`).
4. After `_reset_browser_sync()`, `_open_sync()` is called to restore the
   browser page so subsequent requests do not fail.
5. `_fetch_page_sync` recovery path: when `_sync_page is None` at the top
   of the retry loop, call `_open_sync()` instead of raising immediately.
6. New unit tests verify:
   - The executor is single-threaded (`max_workers=1`).
   - All sync dispatch methods use `run_in_executor` (not `to_thread`).
   - After `_reset_browser_sync`, the browser is re-opened.
   - `close()` shuts down the executor.
7. All existing Liga provider tests continue to pass.
8. `ruff check src/providers/liga/provider.py` passes.

## Files Changed

- `src/providers/liga/provider.py` (all production changes)
- `tests/providers/test_liga_provider_thread_safety.py` (new test file)
