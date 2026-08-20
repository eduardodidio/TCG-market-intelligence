# F09 -- Scheduled Price Collection

**Status:** planned
**Created:** 2026-08-19
**Gandalf Decision:** D-20260819-002

## Summary

Automate recurring price collection via an external cron trigger calling the
existing collect endpoint, protected by an API key guard. Add a health/status
endpoint for observability and a frontend freshness indicator on the Dashboard.
Direction 3 from the brainstorm: external cron + health endpoint, no new
dependencies, no in-process scheduler.

## Waves

| Wave | Tasks       | Description |
|------|-------------|-------------|
| 0    | T01, T02    | Backend: health endpoint (T01) + API key auth guard on collect endpoints (T02). Independent -- T01 adds a new GET route, T02 adds a dependency to existing POST routes. |
| 1    | T03, T04    | Cron trigger script (T03) + frontend freshness indicator on Dashboard (T04). Independent of each other. |
| 2    | T05         | Documentation: diagrams, README update, cron setup docs. |

## Risk Assessment

- **T01 (Health endpoint):** Low risk. New read-only endpoint querying existing
  DB tables. The only complexity is the "stale cards" query, which needs a
  performant SQL aggregation. Mitigated by using existing Repository pattern
  and adding an index-friendly query.

- **T02 (API key guard):** Low risk. Simple FastAPI dependency that reads an
  env var and compares headers. The main concern is not breaking existing tests
  that call collect endpoints without a key -- mitigated by making the guard
  optional when `TCG_API_KEY` is unset.

- **T03 (Cron script):** Low risk. Shell script with curl. Must handle the API
  being down gracefully (non-zero exit). Must work on both Linux/Mac bash and
  Git Bash on Windows.

- **T04 (Frontend freshness):** Low risk. New API call to health endpoint,
  new UI component. Must degrade gracefully if the health endpoint is
  unreachable (show "unknown" instead of crashing).

- **T05 (Docs):** Zero risk. Pure documentation.

## Dependencies

- F06 REST API must be functional (shipped)
- F07 Frontend Dashboard must be functional (shipped)
- F04 collector infrastructure (backfill, update, retry) must work (shipped)
- No external dependencies required
