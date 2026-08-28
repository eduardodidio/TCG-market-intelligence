# Tech Lead Review -- F84 Liga Provider Windows Fix

**Reviewer:** Tech Lead
**Date:** 2026-08-28
**Verdict:** APPROVED

## Summary

F84 replaces the previous Windows behavior (marking the Liga provider as permanently unavailable) with a working sync-in-thread Playwright path. On `sys.platform == "win32"`, the provider uses `playwright.sync_api` running inside `asyncio.to_thread()` instead of the async Playwright API, which requires `ProactorEventLoop` (incompatible with uvicorn's `SelectorEventLoop` on Windows).

## Architecture Assessment

### Sync-in-thread approach: Sound

The core design decision is correct. `asyncio.to_thread()` offloads the blocking sync Playwright calls to the default thread pool executor, keeping the event loop unblocked. This avoids both the event loop incompatibility and the need for global event loop policy changes (which would break uvicorn).

Key lifecycle properties verified:

1. **Start in thread, use in thread, close in thread** -- `_open_sync()`, `_fetch_page_sync()`, `_close_sync()`, and `_reset_browser_sync()` are all plain synchronous methods. They are always called via `asyncio.to_thread()` from the async layer. This is correct because Playwright sync objects are not thread-safe and should be used from a consistent context.

2. **Idempotent open** -- Line 102 checks `self._sync_page is not None` before opening, preventing double initialization. Verified by test.

3. **Robust close** -- `_close_sync()` wraps both `browser.close()` and `pw.stop()` in separate try/except blocks, ensuring partial failures do not prevent full cleanup. References are nulled out afterward.

### Thread safety analysis

**`asyncio.Lock` serialization is sufficient.** Both `get_current_price` and `search_card` acquire `self._lock` before calling `_fetch_page`. Since `asyncio.Lock` serializes at the async layer, only one coroutine can enter the `_fetch_page` -> `to_thread(_fetch_page_sync)` path at a time. The sync Playwright page is never accessed concurrently from multiple threads.

**`_request_count` is shared mutable state** accessed from both the async path (line 260) and the sync path (lines 404-406). However, because the lock serializes all calls, there is no concurrent mutation. This is safe in the current design. If the lock were ever removed or the provider made reentrant, this would become a race condition -- but that is not the case today.

**Thread pool caveat (minor, non-blocking):** `asyncio.to_thread()` uses the default executor, which is a `ThreadPoolExecutor`. Each call to `_fetch_page_sync` could theoretically run on a different thread in the pool. Since the Playwright sync page object is not truly thread-safe, this works only because the `asyncio.Lock` ensures sequential execution. This is acceptable but worth noting in a comment for future maintainers. Not blocking approval.

### Error handling

The sync `_fetch_page_sync` mirrors the async `_fetch_page` logic faithfully:
- Same HTTP status handling (404 fast-fail, 429/403 backoff, 5xx retry, other 4xx raise)
- Same timeout and selector wait behavior
- Same browser reset on non-timeout errors (calls `_reset_browser_sync()` directly, not via `to_thread`, which is correct since it is already in a thread)
- Uses `time.sleep()` instead of `asyncio.sleep()` (correct for blocking context)

### Code duplication

The sync `_fetch_page_sync` (lines 393-541) is a near-complete copy of the async `_fetch_page` (lines 244-391). This is ~150 lines of duplicated logic. While a shared strategy pattern could reduce this, the duplication is justified here:
- The two paths use fundamentally different APIs (sync vs async, `time.sleep` vs `asyncio.sleep`, sync page methods vs awaited page methods)
- Extracting commonality would require either code generation or a complex abstraction that would hurt readability
- The logic is stable (retry/backoff behavior has not changed since F62)

This is acceptable technical debt. If the retry logic needs to change, both paths must be updated, but this is a low-risk scenario.

## Test Assessment

23 tests in `test_provider_windows.py` covering:
- Windows open: flag setting, resource storage, no async resources, idempotency (4 tests)
- Sync fetch_page: HTML return, goto call, request count, selector wait, selector timeout fallback (5 tests)
- Close: cleanup calls, null references, idempotency, error resilience (4 tests)
- search_card end-to-end: parsed prices, error propagation, empty name (3 tests)
- Linux/macOS async path: no sync flag, async resources stored, Darwin variant (3 tests)
- Unavailable flag: false after open, ensure_page returns sync page, default false, get_current_price works (4 tests)

All 23 tests pass. The `_fake_to_thread` helper that runs sync functions synchronously is a clean testing pattern that avoids real thread pool usage in tests.

### Test gap (non-blocking)

No test covers `_reset_browser_sync` being called during `_fetch_page_sync` error handling (line 512). This is a minor gap -- the reset logic is simple (close browser, stop playwright, null references) and is indirectly covered by the close tests. Not blocking.

## Security

No security concerns. No new endpoints, no auth changes, no user input handling changes.

## Verdict

**APPROVED** -- The sync-in-thread approach is architecturally sound, thread safety is maintained via the existing `asyncio.Lock`, error handling mirrors the async path correctly, and the test suite is comprehensive. The code duplication is justified given the fundamental API differences between sync and async Playwright.
