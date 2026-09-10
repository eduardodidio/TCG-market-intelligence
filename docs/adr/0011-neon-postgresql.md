# ADR-0011: Migrate to Neon PostgreSQL for Production

**Status:** accepted
**Date:** 2026-09-10
**Feature:** F119

## Context

Render free tier has no persistent disk. Every deploy or restart wipes the
SQLite database, losing all user data. The push-db workaround (upload local
DB after each deploy) is fragile and error-prone:

- Data lost if push-db runs before deploy finishes
- Data lost if a redeploy happens after push-db
- JWT user_id mismatch requires logout/login after every push-db
- Scheduled task (TEDHC_PushAll) must run daily to keep data in sync

## Decision

Use **Neon** (serverless PostgreSQL) as the production database. Keep SQLite
for local development.

SQLAlchemy's dialect abstraction means application code stays the same. The
engine URL is selected at startup based on the `DATABASE_URL` environment
variable: if set, use PostgreSQL; if absent, fall back to local SQLite.

## Alternatives Considered

| Alternative | Verdict | Reason |
|---|---|---|
| SQLite + Litestream (ADR-0010) | Superseded | Works but adds operational complexity; Cloudflare R2 dependency |
| Render Managed PostgreSQL | Rejected | $7/month minimum, overkill for current scale |
| Supabase | Rejected | Similar to Neon but less generous free tier for compute |
| Keep push-db workflow | Rejected | Fragile, data loss risk on every deploy |

## Consequences

### Positive
- Data persists across Render deploys and restarts
- No more push-db workflow or TEDHC_PushAll scheduled task
- PostgreSQL features: better concurrency, native FK enforcement, full-text search potential
- Neon free tier: 0.5 GB storage, 190 compute-hours/month

### Negative
- Cold start latency ~1-2s after 5 min idle (mitigated by `pool_pre_ping=True`)
- Need to maintain dual-dialect compatibility (SQLite local, PG production)
- `psycopg2-binary` adds ~3 MB to deploy image

## Neon Setup Checklist

1. Create account at [neon.tech](https://neon.tech)
2. Create project "tedhc-market"
3. Copy the **pooled** connection string (with `-pooler` in the hostname)
4. Set `DATABASE_URL` on Render environment variables
5. Run `python scripts/migrate-to-pg.py` to copy existing SQLite data
6. Verify data integrity (row counts, sample queries)
7. Remove `TEDHC_PushAll` scheduled task from Windows Task Scheduler
