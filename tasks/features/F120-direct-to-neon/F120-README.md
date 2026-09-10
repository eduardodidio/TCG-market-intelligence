# F120 — Direct-to-Neon Local Workflow

**Status:** planned
**Created:** 2026-09-10
**Branch:** homol

## Summary

Configure local dev to write directly to Neon PostgreSQL via `.env` file,
eliminating the push-prices workflow entirely. After this feature, the
local workflow becomes:

```
1. Run liga-sweep locally → writes directly to Neon
2. Done. No push needed.
```

## Problem

Even with Neon (F119), the local workflow still requires push-prices to
sync local SQLite prices to the Render API. This is an unnecessary
indirection — if local commands connect directly to Neon, all writes
are immediately available in production.

## Architecture

```
Before (F119):
  Local SQLite → liga-sweep → push-prices → Render API → Neon PG

After (F120):
  Local → liga-sweep → Neon PG ← Render reads directly
```

All CLI commands already use `get_db_url()` which reads `DATABASE_URL`.
Setting `DATABASE_URL` in `.env` makes everything work with zero code changes
in the CLI commands themselves.

## Wave Plan

| Wave | Tasks | Parallelism | Notes |
|------|-------|-------------|-------|
| 0 | T01, T02 | 2 parallel | .env + dotenv loading / push-all.bat + docs |

## Task List

| Task | Summary | Wave | Files |
|------|---------|------|-------|
| T01 | Load .env file + create .env template | 0 | config.py, .env (new, gitignored), .env.example (new) |
| T02 | Update push-all.bat + CLAUDE.md workflow docs | 0 | push-all.bat, CLAUDE.md |

## File Conflict Map

- **config.py** — T01 only (add dotenv loading)
- **.env** — T01 creates (gitignored, user-specific)
- **.env.example** — T01 creates (committed, template without secrets)
- **push-all.bat** — T02 only
- **CLAUDE.md** — T02 only

## Design Decisions

1. **python-dotenv** not needed — just read `.env` manually in `config.py`
   (avoid adding a new dependency for 3 lines of code)
2. **.env already gitignored** — safe to put DATABASE_URL there
3. **.env.example** committed — shows the format without secrets
4. **push-prices kept** in CLI (not deleted) — still works as fallback
5. **push-all.bat** updated to run liga-sweep directly
