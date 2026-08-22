# F37 -- Varredura Global Rotineira (Scheduled Global Scanner)

**Status:** planned
**Created:** 2026-08-21

## Summary

Add automated, configurable scheduling for collection price scans. The system
runs on a single machine and uses APScheduler (in-process) to trigger scans on
cron-like schedules. Schedules are persisted in SQLite so they survive restarts.
Users can create, pause, resume, and delete schedules via CLI, API, and a
frontend dashboard. Every scheduled execution reuses the existing `run_scan`
orchestrator from F13. Error monitoring surfaces failed runs and supports manual
reprocessing.

## User Story

As a collector, I want my collection prices to update automatically on a daily
schedule so I can track market trends without manually triggering scans.

As an operator, I want to configure scan schedules (frequency, filters, time of
day) and monitor their execution history, so I can ensure data freshness and
catch failures early.

## Architecture Impact

### New files

| Layer | File | Purpose |
|-------|------|---------|
| DB model | `src/database/models.py` (extend) | `ScheduledScanRow` table |
| Domain | `src/domain/models.py` (extend) | `ScheduledScan` dataclass |
| Repository | `src/database/repository.py` (extend) | CRUD for scheduled_scans |
| Scheduler | `src/scheduler/service.py` | APScheduler lifecycle (start/stop/add/remove jobs) |
| API schema | `src/api/schemas/schedules.py` | Pydantic request/response models |
| API router | `src/api/routers/schedules.py` | Schedule CRUD + manual trigger endpoints |
| API app | `src/api/app.py` (extend) | Register scheduler on startup/shutdown, mount router |
| CLI | `src/cli/main.py` (extend) | `schedule-list`, `schedule-add`, `schedule-remove` commands |
| Frontend | `frontend/src/api/schedules.ts` | API client for schedule endpoints |
| Frontend | `frontend/src/pages/Schedules.tsx` | Schedule dashboard page |
| Frontend | `frontend/src/components/ScheduleForm.tsx` | Create/edit schedule form |
| Frontend | `frontend/src/components/ScheduleTable.tsx` | Schedule list with status |
| Docs | `docs/diagrams/F37-architecture.mmd` | Scheduler data flow |
| Docs | `docs/diagrams/F37-journey.mmd` | User journey for schedule management |

### Modified files

| File | Change |
|------|--------|
| `src/database/models.py` | Add `ScheduledScanRow` |
| `src/domain/models.py` | Add `ScheduledScan`, `ScheduleStatus` |
| `src/database/repository.py` | Add schedule CRUD methods |
| `src/api/app.py` | Startup/shutdown hooks for scheduler, mount schedules router |
| `src/cli/main.py` | Add schedule management commands |
| `frontend/src/App.tsx` | Add /schedules route |
| `frontend/src/i18n/locales/en.json` | Schedule-related i18n keys |
| `frontend/src/i18n/locales/pt-BR.json` | Schedule-related i18n keys |
| `pyproject.toml` | Add `apscheduler>=3.10` dependency |
| `README.md` | F37 delivery notes |

### Design Decisions

1. **APScheduler 3.x (not 4.x)** -- v3 is stable, well-documented, and supports
   SQLAlchemy job stores out of the box. v4 is alpha. We use
   `BackgroundScheduler` (threading-based) since the API server already runs in
   a single process.

2. **SQLite job store** -- APScheduler's `SQLAlchemyJobStore` persists jobs in
   the same SQLite database. Schedules survive server restarts without external
   infrastructure.

3. **Separate `scheduled_scans` table** -- We store our own schedule metadata
   (name, description, filters, status, last/next run timestamps) rather than
   relying solely on APScheduler's internal job store. This gives us full
   control over the data model and makes the API/frontend simpler.

4. **Reuse `run_scan`** -- Each scheduled execution calls the existing
   `run_scan()` from `src/collectors/scan.py` in a background thread, exactly
   like the manual `POST /scans` endpoint does today. No new scan logic needed.

5. **Single scheduler instance** -- The scheduler is a singleton attached to the
   FastAPI app lifespan. The CLI commands that manage schedules write to the DB;
   the changes take effect next time the API server starts (or via a reload
   endpoint).

## Data Model

```
scheduled_scans
  id              INTEGER PRIMARY KEY
  name            TEXT NOT NULL
  description     TEXT
  cron_expression TEXT NOT NULL        -- e.g. "0 6 * * *" (daily 6am)
  scan_type       TEXT NOT NULL        -- collection|set|format|custom
  filters_json    TEXT DEFAULT '{}'
  status          TEXT NOT NULL        -- active|paused|disabled
  last_run_id     INTEGER              -- FK to scan_runs.id (nullable)
  last_run_at     DATETIME
  next_run_at     DATETIME
  error_count     INTEGER DEFAULT 0    -- consecutive errors
  max_retries     INTEGER DEFAULT 3
  created_at      DATETIME
  updated_at      DATETIME
```

## Constraints

- Only authenticated users can manage schedules (reuse `require_auth_or_api_key`)
- Cron expressions are validated on creation (use `croniter` for parsing)
- Maximum 10 active schedules per user (prevent abuse)
- Minimum interval: 1 hour (no sub-hour cron expressions)
- A running scan blocks the same schedule from triggering a concurrent run
- Error count resets on successful completion
- After `max_retries` consecutive failures, schedule auto-pauses

## Acceptance Criteria

- [ ] `scheduled_scans` table created via SQLAlchemy model
- [ ] APScheduler starts with FastAPI and loads persisted schedules on boot
- [ ] Cron expressions validated on schedule creation (reject invalid or sub-hour)
- [ ] `POST /api/v1/schedules` creates a new schedule
- [ ] `GET /api/v1/schedules` lists all schedules with last/next run info
- [ ] `PATCH /api/v1/schedules/{id}` updates cron, filters, or status (pause/resume)
- [ ] `DELETE /api/v1/schedules/{id}` removes a schedule
- [ ] `POST /api/v1/schedules/{id}/trigger` manually runs a schedule immediately
- [ ] Scheduled scan creates a `scan_runs` entry (reuses F13 infrastructure)
- [ ] `schedule-list` CLI lists active schedules
- [ ] `schedule-add` CLI creates a schedule from command line
- [ ] `schedule-remove` CLI removes a schedule by ID
- [ ] Frontend Schedules page shows list with status, cron, last/next run
- [ ] Frontend form allows creating/editing schedules
- [ ] Auto-pause after N consecutive failures, with visual indicator
- [ ] All existing tests pass (1189+ backend, 520+ frontend)
- [ ] New tests added for all layers (coverage >= 90%)
- [ ] README.md updated with F37 delivery notes
- [ ] Diagrams created: F37-architecture.mmd, F37-journey.mmd

## Tasks

| Task | File | Wave | Description |
|------|------|------|-------------|
| T01 | F37-T01.md | 0 | Domain models + DB table (`ScheduledScan`, `ScheduledScanRow`) |
| T02 | F37-T02.md | 0 | Add `apscheduler` + `croniter` dependencies |
| T03 | F37-T03.md | 1 | Repository CRUD for `scheduled_scans` |
| T04 | F37-T04.md | 2 | Scheduler service (`src/scheduler/service.py`) |
| T05 | F37-T05.md | 3 | API schemas + router (`/api/v1/schedules`) |
| T06 | F37-T06.md | 3 | CLI commands (`schedule-list`, `schedule-add`, `schedule-remove`) |
| T07 | F37-T07.md | 3 | FastAPI lifespan integration (startup/shutdown hooks) |
| T08 | F37-T08.md | 4 | Frontend API client + Schedules page |
| T09 | F37-T09.md | 5 | Diagrams, README, i18n keys |

## Waves

- **Wave 0** (T01, T02 -- parallel): Domain models + dependency setup
- **Wave 1** (T03): Repository layer -- depends on T01
- **Wave 2** (T04): Scheduler service -- depends on T03
- **Wave 3** (T05, T06, T07 -- parallel): API + CLI + lifespan -- depends on T04
- **Wave 4** (T08): Frontend -- depends on T05
- **Wave 5** (T09): Documentation -- depends on all

## File Conflicts

- `src/database/models.py` -- T01 only
- `src/domain/models.py` -- T01 only
- `src/database/repository.py` -- T03 only
- `src/api/app.py` -- T07 only
- `src/cli/main.py` -- T06 only
- No Wave-internal conflicts on shared files
