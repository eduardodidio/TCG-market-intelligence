# F76 — Playwright Windows Startup Fix

**Status:** planned
**Wave structure:** Wave 0 (parallel with F72, F73)
**Dependencies:** None

## Summary

Fix the noisy `NotImplementedError` traceback on Windows when Playwright tries to start via asyncio subprocess. The app works fine (Liga is skipped), but the console output is ugly.

## Tasks

| Task | Description | Wave |
|------|-------------|------|
| F76-T01 | Suppress Playwright startup error on Windows | 0 |

## Acceptance Criteria

- No "Task exception was never retrieved" traceback on Windows startup
- Clean warning log line only (e.g., "Liga provider skipped: platform does not support async subprocesses")
- Liga provider still works on Linux/macOS if available
- App starts cleanly on Windows
