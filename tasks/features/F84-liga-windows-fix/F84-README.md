# F84 — Liga Provider Windows Fix

**Status:** done
**Wave structure:** Wave 0 (parallel with F83)
**Dependencies:** None

## Summary

The LigaMagicProvider permanently disables itself on Windows (`sys.platform == "win32"`) because Playwright's async API requires `asyncio.create_subprocess_exec` which is not supported by Windows' default `SelectorEventLoop`. The fix uses Playwright's **sync API** wrapped in `asyncio.to_thread()` so it runs in a background thread, avoiding the event loop limitation entirely.

## Tasks

| Task | Description | Wave |
|------|-------------|------|
| F84-T01 | Replace async Playwright with sync-in-thread on Windows | 0 |
| F84-T02 | Backend tests for Windows sync provider path | 0 |

## Acceptance Criteria

- Liga provider works on Windows (no "unavailable on this platform" error)
- Liga provider still works on Linux/macOS via async API (no regression)
- `search_card`, `get_current_price`, `get_price_history` all work on Windows
- Rate limiting, retry logic, and error handling preserved
- Browser lifecycle (open/close) works correctly in thread
- No global event loop policy changes (would break uvicorn)
- Existing Liga tests pass
