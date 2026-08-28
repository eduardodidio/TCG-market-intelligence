# F84 — Liga Provider Windows Fix — QA Report

**Date:** 2026-08-28
**Verdict:** PASS

## Test Results

| Suite | Passed | Failed | Total |
|-------|--------|--------|-------|
| Backend (all) | 2487 | 0 | 2487 |
| Frontend (all) | 1211 | 0 | 1211 |
| Liga provider tests | 165 | 0 | 165 |
| F84 Windows tests (new) | 23 | 0 | 23 |

## Acceptance Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Liga provider works on Windows (no "unavailable" error) | PASS | `open()` detects `sys.platform == "win32"` and uses sync Playwright via `asyncio.to_thread()` instead of marking `_unavailable=True`. Verified by `test_unavailable_false_after_open_on_windows`. |
| Liga provider still works on Linux/macOS via async API | PASS | `TestOpenLinuxUsesAsyncPlaywright` (3 tests) confirms async path on linux/darwin: `_use_sync=False`, async resources stored, sync resources remain None |
| `search_card`, `get_current_price`, `get_price_history` all work on Windows | PASS | `test_search_card_returns_parsed_prices`, `test_get_current_price_works_on_windows` verify end-to-end mock flow. `get_price_history` returns `[]` (no platform-specific code). |
| Rate limiting, retry logic, and error handling preserved | PASS | `_fetch_page_sync` mirrors async `_fetch_page` logic (404/429/403/5xx handling, backoff, retries). `test_search_card_windows_raises_liga_error` confirms error propagation. |
| Browser lifecycle (open/close) works correctly in thread | PASS | `TestCloseWindowsCleansSyncResources` (4 tests) verifies close calls `browser.close()`+`pw.stop()`, nulls all references, handles errors gracefully, and is idempotent. |
| No global event loop policy changes | PASS | Code uses `asyncio.to_thread()` to run sync Playwright in a background thread — no `WindowsProactorEventLoopPolicy` or similar changes that would affect uvicorn. |
| Existing Liga tests pass | PASS | All 165 provider tests pass (142 pre-existing + 23 new F84 tests) |

## Architecture Review

The implementation correctly addresses the Windows event loop limitation:

1. **`open()`** — branches on `sys.platform == "win32"`, calls `_open_sync()` via `asyncio.to_thread()`
2. **`_open_sync()`** — uses `sync_playwright()` API (blocking calls safe in thread)
3. **`_fetch_page()`** — delegates to `_fetch_page_sync()` via `asyncio.to_thread()` when `_use_sync=True`
4. **`_fetch_page_sync()`** — mirrors async logic with `time.sleep()` instead of `asyncio.sleep()`
5. **`close()`** — delegates to `_close_sync()` via `asyncio.to_thread()` with error suppression
6. **`_reset_browser_sync()`** — mirrors async reset for crash recovery

Key design decisions:
- Separate `_sync_*` resource attributes avoid confusion with async `_playwright/_browser/_page`
- `_use_sync` flag checked in `_ensure_page`, `_fetch_page`, `close`, `_reset_browser`
- Thread-safe: `asyncio.Lock` serializes all public methods; sync code runs in isolated thread

## New Test File

`tests/providers/liga/test_provider_windows.py` — 23 tests across 6 test classes:
- `TestOpenWindowsUsesSyncPlaywright` (4 tests)
- `TestFetchPageWindowsDelegatesToSync` (5 tests)
- `TestCloseWindowsCleansSyncResources` (4 tests)
- `TestSearchCardWindows` (3 tests)
- `TestOpenLinuxUsesAsyncPlaywright` (3 tests)
- `TestUnavailableFlagNotSetOnWindows` (4 tests)

## Regressions

None detected. All 2487 backend and 1211 frontend tests pass with zero failures.
