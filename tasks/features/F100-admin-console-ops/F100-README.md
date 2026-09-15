# F100 -- Admin Console Operations

**Status:** planned

## Summary

Add operational capabilities to the Admin Console: trigger background jobs
(collection scan, Liga sweep, catalog scan) from the UI, download SQLite
DB backups, and track admin actions in an audit log with a filterable view.

## Problem

Admins currently rely on the CLI or direct API calls to trigger operational
jobs (Liga sweeps, catalog scans). There is no way to download a DB backup
from the UI. Admin actions (credit grants, user deletions, job triggers)
are not tracked -- if something goes wrong there is no audit trail.

## Goals

1. New `audit_log` table to record admin actions with actor, action, target,
   details, and timestamp
2. Audit log service that can be called from any admin endpoint
3. Retrofit existing admin endpoints (credit adjust, user create/delete) to
   log actions
4. Admin-only API endpoints for: trigger Liga scan, trigger catalog scan,
   download DB backup, list/filter audit log
5. Frontend: "Operations" accordion section in AdminPanel with job trigger
   buttons and scan status feedback
6. Frontend: "Audit Log" accordion section with filterable table

## Waves

### Wave 0 -- DB Schema (audit_log table)
| Task | Description |
|------|-------------|
| T01  | AuditLogRow model + Alembic-free migration |

### Wave 1 -- Backend Services + API (parallelizable)
| Task | Description |
|------|-------------|
| T02  | Audit log service + repository methods |
| T03  | Admin job trigger endpoints (Liga scan, catalog scan) |
| T04  | DB backup download endpoint |
| T05  | Retrofit existing admin endpoints with audit logging |

### Wave 2 -- Frontend UI (depends on Wave 1)
| Task | Description |
|------|-------------|
| T06  | AdminOperationsSection (job triggers + status) |
| T07  | AdminAuditLogSection (filterable table) |

## Dependency Map

```
T01 (audit_log table)
 |
 +-- T02 (audit service)  --+-- T05 (retrofit existing endpoints)
 |                           |
 +-- T03 (job triggers)      +-- T06 (operations UI)
 |                           |
 +-- T04 (DB backup)         +-- T07 (audit log UI)
```

T03 and T04 have no dependency on T02 (they work without audit logging).
T05 depends on T02. T06 depends on T03 + T04. T07 depends on T02 + T05.

## Key Architectural Decisions

- The `audit_log` table uses a simple flat structure (no FK to users table)
  so it survives user deletion and has zero coupling to auth.
- Job triggers reuse the existing `run_liga_scan` and `liga_sweep` functions
  in background threads (same pattern as `scans.py` router).
- DB backup is a simple file copy of the SQLite file, served as a download.
  No streaming or incremental backup -- the DB is small (<100MB).
- Audit logging is fire-and-forget (best-effort). Failure to log must never
  block the admin action itself.
- Catalog scan trigger calls `liga_sweep` with `collection_only=False`,
  reusing the existing catalog sweep infrastructure.

## Files Likely Modified

- `src/database/models.py` (AuditLogRow)
- `src/database/repository.py` (audit log CRUD)
- `src/services/audit.py` (new -- audit log service)
- `src/api/routers/admin.py` (new endpoints, retrofit existing)
- `frontend/src/api/admin.ts` (new API functions)
- `frontend/src/components/admin/AdminOperationsSection.tsx` (new)
- `frontend/src/components/admin/AdminAuditLogSection.tsx` (new)
- `frontend/src/pages/AdminPanel.tsx` (add new accordion sections)
- `frontend/src/locales/en/translation.json` (i18n keys)
- `frontend/src/locales/pt/translation.json` (i18n keys)
