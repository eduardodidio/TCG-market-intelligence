# T01 -- Replace asyncio.to_thread with dedicated single-thread executor

**Status:** planned
**Wave:** 0

## User Story

As a developer, I want all sync Playwright operations in `LigaMagicProvider`
to run on a single dedicated thread, so that the greenlet thread-affinity
requirement is satisfied and sweeps no longer crash on Windows.

## Dev Notes

**File:** `src/providers/liga/provider.py`

### 1. Add import

At the top of the file, add:

```python
from concurrent.futures import ThreadPoolExecutor
```

### 2. Create executor in `__init__` (line ~84)

After `self._last_page_url: str | None = None` (line 101), add:

```python
self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="liga-pw")
```

### 3. Replace ALL `asyncio.to_thread()` calls

There are exactly **4** call sites to replace. Each follows the same
pattern -- replace `await asyncio.to_thread(fn, ...)` with
`await asyncio.get_running_loop().run_in_executor(self._executor, fn, ...)`.

To avoid repeating `asyncio.get_running_loop()` everywhere, add a small
helper method:

```python
async def _run_sync(self, fn, *args):
    """Run a sync function on the dedicated Playwright thread."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(self._executor, fn, *args)
```

Then replace each call site:

| Location | Old | New |
|----------|-----|----|
| `open()` line 124 | `await asyncio.to_thread(self._open_sync)` | `await self._run_sync(self._open_sync)` |
| `close()` line 159 | `await asyncio.to_thread(self._close_sync)` | `await self._run_sync(self._close_sync)` |
| `_reset_browser()` line 221 | `await asyncio.to_thread(self._reset_browser_sync)` | `await self._run_sync(self._reset_browser_sync)` |
| `_fetch_page()` line 270 | `await asyncio.to_thread(self._fetch_page_sync, url)` | `await self._run_sync(self._fetch_page_sync, url)` |
| `_select_edition()` line 874 | `await asyncio.to_thread(self._select_edition_sync, edition_value)` | `await self._run_sync(self._select_edition_sync, edition_value)` |

**Note:** That is 5 call sites total (open, close, reset_browser, fetch_page, select_edition).

### 4. Shutdown executor in `close()`

After the sync browser is closed (after `await self._run_sync(self._close_sync)`),
shut down the executor:

```python
self._executor.shutdown(wait=False)
```

### 5. Add browser recovery after reset

In `_reset_browser()` (the async wrapper, line ~218), after the
`await self._run_sync(self._reset_browser_sync)` call and the
`await asyncio.sleep(0.5)`, add recovery:

```python
try:
    await self._run_sync(self._open_sync)
    log.info("liga_browser_recovered", sync=True)
except Exception as e:
    log.warning("liga_browser_recovery_failed", error=str(e))
```

### 6. Recovery in `_fetch_page_sync` retry loop

In `_fetch_page_sync()` (line ~430), replace the immediate error raise
when `self._sync_page is None` with a recovery attempt:

```python
if self._sync_page is None:
    try:
        self._open_sync()
    except Exception:
        raise LigaError(
            "Sync page not available and recovery failed",
            url=url,
            status_code=0,
            attempts=attempt,
        )
```

This handles the case where `_reset_browser_sync` was called directly from
`_fetch_page_sync`'s own exception handler (line 534), which runs on the
Playwright thread already (no async wrapper), so the recovery in
`_reset_browser()` would not apply.

### 7. Update module docstring

Update the module docstring (lines 1-8) to mention the dedicated executor
instead of `asyncio.to_thread()`.

## Testing

- Covered by T02 (dedicated test file).
- Run `ruff check src/providers/liga/provider.py` to verify no lint errors.
- Run `pytest tests/providers/test_liga_provider.py -x` to verify existing
  tests still pass.
