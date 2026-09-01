# F94 — Collection Persistence (SQLite Backup/Restore)

**Status:** done
**Priority:** critical
**Estimate:** 4 tasks, 2 waves

## Problem

Render free tier does NOT support persistent disks. The `disk` block in
`render.yaml` is ignored on the free plan. Every time the service spins down
(15 min of inactivity) or redeploys, the container filesystem is recreated
from scratch and the SQLite database at `/data/tcg_market.db` is lost —
including the entire collection, users, prices, decks, credits, etc.

## Solution Analysis

| Alternative | Cost | Complexity | Latency | Verdict |
|---|---|---|---|---|
| **A. Litestream (S3/R2 replication)** | R2 free tier (10GB) | Medium — binary install, sidecar | ~0 (continuous WAL streaming) | **CHOSEN** |
| B. Cron dump to S3/R2 | R2 free tier | Low | Data loss = last interval | Good fallback |
| C. Managed PostgreSQL (Render/Neon/Supabase) | Free tiers exist | High — ORM migration, dialect differences | Network hop | Over-engineered for now |
| D. JSON/CSV export | Free | Low | Full load on startup | Fragile, doesn't scale |
| E. Upgrade to Render paid ($7/mo) | $7/mo | Zero | Zero | User decision |

### Chosen: Litestream + Cloudflare R2

**Litestream** is a standalone tool that continuously replicates a SQLite
database to S3-compatible storage by streaming WAL changes. On startup, it
restores the latest snapshot + WAL segments, then launches the app.

- **Zero data loss** (WAL streaming, not periodic dumps)
- **Transparent** to the app (no code changes to SQLite usage)
- **R2 free tier** — 10GB storage, 10M class B ops/mo, zero egress
- **Dockerfile change only** — install litestream binary, wrap `CMD`
- **Fallback** — if R2 is unreachable, app starts with empty DB (same as today)

### Architecture

```
[App writes SQLite] --> [Litestream WAL stream] --> [Cloudflare R2 bucket]
                                                          |
[Container starts] --> [Litestream restore] --> [SQLite ready] --> [App boots]
```

## Waves

### Wave 0 — Infrastructure (2 tasks, parallel)
- T01: Litestream Dockerfile integration
- T02: Litestream config + Render env vars

### Wave 1 — Safety net (2 tasks, parallel)
- T03: CLI manual backup/restore commands (R2)
- T04: Health check + monitoring

## Environment Variables (new)

| Var | Example | Required |
|---|---|---|
| `LITESTREAM_REPLICA_URL` | `s3://tcg-backup/db` | Yes |
| `LITESTREAM_ACCESS_KEY_ID` | (R2 token) | Yes |
| `LITESTREAM_SECRET_ACCESS_KEY` | (R2 secret) | Yes |
| `LITESTREAM_ENDPOINT` | `https://<acct>.r2.cloudflarestorage.com` | Yes |

## Risks

- **First deploy**: no backup exists yet, so Litestream restore is a no-op
  (app starts fresh, which is fine — user re-imports collection)
- **Concurrent writes**: SQLite WAL mode handles single-writer correctly;
  Litestream is designed for this
- **R2 outage**: Litestream buffers locally and retries; worst case, app
  runs without replication temporarily
