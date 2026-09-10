# F119 — Migrate to Neon PostgreSQL

**Status:** planned
**Created:** 2026-09-10
**Branch:** homol

## Summary

Replace SQLite with Neon (serverless PostgreSQL) as the production database.
Keep SQLite for local development. The push-db/push-prices workflow becomes
obsolete — Neon persists data across Render deploys/restarts.

## Problem

Render free tier has no persistent disk. Every deploy/restart wipes the
SQLite DB. The current workaround (push-db after every deploy) is fragile,
error-prone, and requires manual intervention. Users lose their collection
if the sequence is not followed exactly.

## Architecture

```
Local dev:  SQLite (sqlite:///tcg_market.db)  — zero setup
Render:     Neon PostgreSQL (DATABASE_URL)     — persistent, serverless
```

Both dialects supported via a thin abstraction layer:
- `dialect_insert()` helper selects `sqlite.insert` or `postgresql.insert`
- PRAGMAs and VACUUM guarded with `is_sqlite()` check
- Raw SQL in catalog.py uses `||` concat (works in both dialects)
- FK constraints enforced by model definitions (PG native, SQLite via PRAGMA)

## Audit of SQLite-Specific Code

| Location | Issue | Action |
|----------|-------|--------|
| `repository.py` L8 | `sqlite_insert` import (5 usages) | → `dialect_insert()` |
| `repository.py` L58-65 | `PRAGMA foreign_keys=ON` | Guard with `is_sqlite()` |
| `repository.py` L140-201 | `_ensure_fk_constraints()` (PRAGMA-based table rebuild) | Guard — PG has native FKs |
| `seeder.py` L17 | `sqlite_insert` (2 usages) | → `dialect_insert()` |
| `seeder.py` L39-47 | `PRAGMA foreign_keys + WAL` | Guard |
| `achievements.py` L8 | `sqlite_insert` (2 usages) | → `dialect_insert()` |
| `catalog.py` L107+ | `'liga_' \|\| CAST(c.id AS TEXT)` | Works in PG too (no change) |
| `cleanup.py` | `VACUUM` (4 usages) | Guard — PG auto-vacuums |
| `cli/main.py` L1314 | `VACUUM` | Guard |
| `config.py` | `get_db_url()` defaults to sqlite | Support `DATABASE_URL` env var |
| `backup.py` | `sqlite3.backup()` API | Guard — PG uses pg_dump |
| `admin.py` L437+ | SQLite backup download endpoint | Guard |
| `db_sync.py` | SQLite file upload/restore | Guard — not needed for PG |
| `cli/main.py` L1596+ | `push-db` command | Deprecate (SQLite-only) |
| `cli/main.py` L1448+ | `push-prices` command | Keep (still useful for remote price sync) |

## Wave Plan

| Wave | Tasks | Parallelism | Notes |
|------|-------|-------------|-------|
| 0 | T01 | 1 | Engine abstraction + dependencies |
| 1 | T02, T03, T04 | 3 parallel | Code migration (no file overlap) |
| 2 | T05 | 1 | Data migration script + Neon setup |
| 3 | T06 | 1 | Tests |

## Task List

| Task | Summary | Wave | Files |
|------|---------|------|-------|
| T01 | Engine abstraction layer + psycopg2-binary dep | 0 | config.py, requirements.txt, new: database/compat.py |
| T02 | Repository + achievements upsert migration | 1 | repository.py, achievements.py |
| T03 | Seeder + catalog + cleanup dialect guards | 1 | seeder.py, catalog.py, cleanup.py |
| T04 | Guard SQLite-only features (backup, db_sync, push-db, VACUUM) | 1 | backup.py, admin.py, db_sync.py, cli/main.py |
| T05 | Data migration script (SQLite → Neon PG) + setup docs | 2 | scripts/migrate-to-pg.py (new), docs/adr/ |
| T06 | Tests for dual-dialect support | 3 | tests/ |

## File Conflict Map

- **config.py** — T01 only
- **database/compat.py** — T01 creates (new)
- **requirements.txt** — T01 only
- **repository.py** — T02 only
- **achievements.py** — T02 only
- **seeder.py** — T03 only
- **catalog.py** — T03 only
- **cleanup.py** — T03 only
- **backup.py** — T04 only
- **admin.py** — T04 only
- **db_sync.py** — T04 only
- **cli/main.py** — T04 only
- **scripts/migrate-to-pg.py** — T05 creates (new)
- **docs/adr/** — T05 creates new ADR

## Design Decisions

1. **Dual-dialect, not PG-only** — local dev stays SQLite for simplicity
2. **No Alembic yet** — `create_all()` still handles schema. Alembic can be added later.
3. **`dialect_insert()` helper** — thin wrapper, not a full abstraction layer
4. **push-db deprecated, not deleted** — still works for SQLite→SQLite sync if needed
5. **Neon connection pooling** — use `?sslmode=require` + SQLAlchemy pool settings
6. **`||` concat in raw SQL** — works identically in SQLite and PostgreSQL
