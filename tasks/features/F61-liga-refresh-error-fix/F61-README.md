# F61 — Liga Refresh Error Fix

**Status:** done
**Created:** 2026-08-25
**Priority:** P1 (user-facing bug — Liga refresh silently fails)

## Summary

The `POST /collection/{id}/refresh-liga` endpoint catches a generic `Exception`
with an empty `str()` representation when Playwright fails in the uvicorn
server context. The user sees `"Unexpected error: "` with no useful info, and
the price is not updated. The same card works fine when tested standalone
(outside the server's event loop), pointing to a server-context-specific issue
with Playwright lifecycle management.

## User Story

As a collector, when I click the Liga refresh button on a card detail page, I
want either a successful price update or a clear, actionable error message —
not a blank `"Unexpected error: "` that gives me no idea what happened.

## Root Cause Analysis

Investigation findings:
1. The endpoint at `src/api/routers/collection.py:898-926` creates a new
   `LigaMagicProvider()` per request and calls `search_card(card_name)`
2. The generic `except Exception as exc:` at line 920 catches something with
   `str(exc) == ""` — likely a Playwright `Error("")` or similar
3. The same flow works perfectly when run standalone via `asyncio.run()`
4. The server context has a **singleton** `LigaMagicProvider` in the
   `ProviderRegistry` (created at startup via `create_registry_from_env()`).
   Creating a second transient instance per request may cause Playwright
   resource conflicts (multiple browser processes, port collisions)
5. The `finally: await provider.close()` always runs, but the exception
   occurs before `close()` (inside `search_card`)
6. The error logging at line 921 only logs `str(exc)` — no exception type,
   no traceback, making diagnosis impossible

## Acceptance Criteria

1. Liga refresh returns a clear, descriptive error message (includes exception
   type and relevant context) when it fails
2. Server logs include full traceback + exception type for Liga errors
3. The endpoint reuses the singleton `LigaMagicProvider` from the registry
   instead of creating a new instance per request (fixes the root cause)
4. Playwright-specific exceptions are caught explicitly in the provider's
   `search_card` method (defense in depth)
5. Frontend displays the improved error message correctly
6. Existing Liga scan/sweep tests continue to pass

## Architecture Decisions

- **Reuse singleton provider**: The `refresh-liga` endpoint should use the
  `LigaMagicProvider` from `app.state.provider_registry` instead of creating
  a new instance. This avoids Playwright resource conflicts.
- **No new dependencies**: Pure bug fix, no new packages needed.
- **Defense in depth**: Add Playwright exception handling at both provider
  level (search_card) and endpoint level (catch-all with traceback).

## Waves

| Wave | Tasks | Description |
|------|-------|-------------|
| 0    | T01, T02 | Provider hardening + endpoint fix (parallel) |
| 1    | T03 | Frontend error display improvement |

## Tasks

- **T01** (Wave 0): Harden `search_card` Playwright exception handling
- **T02** (Wave 0): Fix `refresh-liga` endpoint — reuse singleton + better errors
- **T03** (Wave 1): Frontend error message display + i18n
