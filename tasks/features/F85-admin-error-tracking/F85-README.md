# Feature F85 — Admin Error Tracking & Structured Error Logs

**Status:** done
**Owner:** @architect
**PRD:** (inline — feature is self-contained)

## Goal

Capture all application errors (unhandled exceptions, provider failures,
scan errors) into structured JSON log files designed for Claude-assisted
diagnosis, and expose them through an admin dashboard with filtering,
pagination, and detail views.

## Architecture impact

| Layer | Changes |
|-------|---------|
| `src/errors/` | NEW — error store (SQLite table), error logger service, retention cleanup |
| `src/api/routers/admin.py` | Extended — two new endpoints under `/admin/errors` |
| `src/api/schemas/admin.py` | Extended — error list/detail response schemas |
| `src/api/app.py` | Modified — generic exception handler calls error logger; middleware captures request context |
| `src/cli/main.py` | Extended — `error-cleanup` CLI command |
| `frontend/src/api/admin.ts` | Extended — error API client functions |
| `frontend/src/components/admin/AdminErrorsSection.tsx` | NEW — error list+detail accordion section |
| `frontend/src/pages/AdminPanel.tsx` | Modified — includes new errors accordion |
| `logs/errors/` | NEW — structured JSON error log files (gitignored) |

## Design decisions

### Error storage: SQLite table (not just files)

Errors are stored in an `error_log` SQLite table for queryability
(filtering, pagination, date ranges). Additionally, a JSON Lines file
(`logs/errors/errors.jsonl`) is appended for offline Claude analysis.
The JSONL file is the "Claude-ready" artifact; the DB table powers the
admin UI.

### Claude-ready error format

Each error entry contains:
```json
{
  "id": "uuid",
  "timestamp": "ISO-8601",
  "level": "ERROR|CRITICAL|WARNING",
  "error_type": "ValueError",
  "message": "invalid literal for int()",
  "traceback": "full traceback string",
  "module": "src.providers.liga.provider",
  "function": "fetch_price",
  "line": 142,
  "request_context": {
    "method": "POST",
    "path": "/api/v1/collection/42/refresh",
    "user_id": 1,
    "request_id": "uuid",
    "params": {}
  },
  "extra": {}
}
```

This structure gives Claude: the exact error, where it happened, the
call stack, and the request that triggered it. No additional context
gathering needed.

### Retention

Configurable via env vars:
- `TCG_ERROR_MAX_AGE_DAYS` (default: 30)
- `TCG_ERROR_MAX_ENTRIES` (default: 10000)

Auto-cleanup runs on app startup and via CLI.

## Waves

- **Wave 0**: F85-T01, F85-T02, F85-T03  (DB model, error service, JSONL writer — all independent)
- **Wave 1**: F85-T04, F85-T05            (API endpoints + app.py integration — depend on T01+T02)
- **Wave 2**: F85-T06, F85-T07            (frontend section + CLI cleanup — T06 depends on T04/T05, T07 depends on T02)
- **Wave 3**: F85-T08                     (backend + frontend tests)

## Global acceptance criteria

- [ ] All unhandled exceptions in API requests are captured with full context
- [ ] Provider errors (MYP, Liga) during scans are captured
- [ ] Errors are written to both SQLite and JSONL
- [ ] Admin can view, filter, and inspect errors via the UI
- [ ] JSONL file is structured for direct Claude consumption
- [ ] Old errors are cleaned up based on retention config
- [ ] All tasks implemented and tested
- [ ] Tech Lead approved
- [ ] QA passed

## Diagrams

- `docs/diagrams/F85-architecture.mmd`
- `docs/diagrams/F85-journey.mmd`
