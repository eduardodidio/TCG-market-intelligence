# F62 — Liga Provider Resilience

**Status:** done
**Created:** 2026-08-26
**Priority:** P1 (user-facing bug — Liga refresh fails with NotImplementedError)

## Summary

Despite F61's fixes, the `POST /collection/{id}/refresh-liga` endpoint still
fails with `"LigaMagic error: Unexpected NotImplementedError (no message)"`.
F61 improved error messages and reused the singleton provider, but the
`_fetch_page()` exception handler remains too narrow — it only catches
`TimeoutError | OSError | PlaywrightError`, letting `NotImplementedError`
(and any other non-covered exception) escape unhandled.

Additionally, the singleton `LigaMagicProvider` in the registry has no
lifecycle management (browser never opened at startup, never closed on
shutdown), no concurrency guard (single Playwright page shared across
concurrent requests), and `_reset_browser()` can leave stale state that
causes re-open failures.

## Root Cause Analysis

1. **`_fetch_page` except clause too narrow**: Catches only
   `(TimeoutError, OSError, PlaywrightError)`. A `NotImplementedError` is
   a subclass of `RuntimeError`, not any of those — it escapes to
   `search_card`'s generic handler which wraps it as a `LigaError` with
   the unhelpful "Unexpected NotImplementedError (no message)" text.

2. **No browser lifecycle for singleton**: `create_registry_from_env()`
   creates `LigaMagicProvider()` but never calls `open()`. The lifespan
   never calls `close()` on shutdown. The browser starts lazily on first
   request via `_ensure_page()`, but in the uvicorn async context this
   lazy init may hit edge cases (event loop state, subprocess issues).

3. **No concurrency guard**: The singleton shares a single Playwright
   `Page` object. Two concurrent `refresh-liga` requests would navigate
   the same page simultaneously, causing race conditions and potential
   Playwright internal errors (including `NotImplementedError`).

4. **`_reset_browser` re-open fragility**: After `_reset_browser()` sets
   all internal state to `None`, the next `_ensure_page()` call tries to
   start a fresh Playwright subprocess. If the old process hasn't fully
   exited, this can fail with various errors.

## Acceptance Criteria

1. `_fetch_page()` catches ALL exceptions from Playwright operations
   (broad `except Exception` with proper logging), not just 3 specific types
2. Singleton provider browser opens during FastAPI lifespan startup and
   closes on shutdown
3. Concurrent refresh-liga requests are serialized via an asyncio lock
4. `_reset_browser()` waits briefly for cleanup before re-opening
5. Error messages include exception type + traceback in server logs
6. Frontend still displays clear error with MYP fallback hint
7. All existing Liga tests pass

## Architecture Decisions

- **Broad catch in `_fetch_page`**: Change `except (TimeoutError, OSError, PlaywrightError)` to `except Exception` with proper categorization inside the handler. This is defense-in-depth — Playwright can raise many exception types.
- **Lifespan lifecycle**: Call `provider.open()` in FastAPI lifespan, `provider.close()` on shutdown. Removes lazy-init edge cases.
- **asyncio.Lock**: Add a lock to `LigaMagicProvider` to serialize page access. Playwright pages are not concurrent-safe.
- **No new dependencies**: Pure bug fix.

## Waves

| Wave | Tasks | Description |
|------|-------|-------------|
| 0    | T01   | Broaden _fetch_page exception handling + add asyncio.Lock |
| 0    | T02   | Lifespan lifecycle management for singleton provider |

## Tasks

- **T01** (Wave 0): Broaden `_fetch_page` exception handler + add concurrency lock
- **T02** (Wave 0): Provider lifecycle in FastAPI lifespan (open/close)
