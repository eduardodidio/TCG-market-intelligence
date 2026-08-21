# F13 -- Buscas por Colecao (Collection Scans)

**Status:** done

## Summary

Add independent, filterable scan execution with full metrics tracking.
Users can trigger scans by collection, set, format, or custom card list,
and each execution is persisted with start/end timestamps, status, card
counts, and error details. Replaces ad-hoc snapshot/sync commands with a
unified scan model that supports history and auditing.

## Architecture Impact

- `src/domain/models.py` -- new `ScanStatus`, `ScanType`, `ScanFilter`, `ScanRun` models
- `src/database/models.py` -- new `ScanRunRow` table
- `src/database/repository.py` -- CRUD for scan_runs + filtered card queries
- `src/collectors/scan.py` -- **new file**, generic scan orchestrator
- `src/cli/main.py` -- new `scan` and `scan-history` commands
- `src/api/schemas/scans.py` -- **new file**, Pydantic schemas
- `src/api/routers/scans.py` -- **new file**, scan endpoints
- `frontend/src/pages/Scans.tsx` -- **new file**, scan management page
- `frontend/src/components/ScanForm.tsx` -- **new file**
- `frontend/src/components/ScanHistoryTable.tsx` -- **new file**
- `frontend/src/hooks/useScans.ts` -- **new file**

## Wave Manifest

- **Wave 0**: F13-T01, F13-T02        (domain models + DB table, parallel)
- **Wave 1**: F13-T03                  (repository methods, depends on T01+T02)
- **Wave 2**: F13-T04                  (scan orchestrator, depends on T03)
- **Wave 3**: F13-T05, F13-T06, F13-T07 (CLI + API schemas + API endpoints, parallel)
- **Wave 4**: F13-T08                  (frontend scans page)
- **Wave 5**: F13-T09                  (diagrams + documentation)

## Global Acceptance Criteria

- [ ] Scan runs are persisted in `scan_runs` table with full metrics
- [ ] Scans can filter by collection, set_code, format, rarity, card IDs
- [ ] `scan` CLI triggers a scan with filter options and prints summary
- [ ] `scan-history` CLI lists past scan runs with metrics
- [ ] `POST /api/v1/scans` triggers a background scan
- [ ] `GET /api/v1/scans` lists scan history with pagination
- [ ] `GET /api/v1/scans/{id}` returns scan detail with error summary
- [ ] Frontend Scans page shows history and allows triggering new scans
- [ ] All existing tests pass (715+ backend, 192+ frontend)
- [ ] New tests added for all layers (coverage >= 90%)
- [ ] README.md updated with F13 delivery notes

## Diagrams

- `docs/diagrams/F13-architecture.mmd` -- scan orchestrator data flow
- `docs/diagrams/F13-journey.mmd` -- user journey for triggering and monitoring scans
