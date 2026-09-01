# ADR-0010: SQLite Persistence via Litestream + Cloudflare R2

**Status:** accepted
**Date:** 2026-08-31
**Feature:** F94

## Context

Render free tier does not support persistent disks. The `disk` block in
`render.yaml` is ignored, and the container filesystem is ephemeral. Every
spin-down (15 min of inactivity) or redeploy destroys the SQLite database,
losing all user data (collection, prices, decks, credits, users).

## Decision

Use **Litestream** to continuously replicate the SQLite WAL to a
**Cloudflare R2** bucket (S3-compatible). On container startup, Litestream
restores the latest snapshot before launching the application.

## Alternatives Considered

| Alternative | Verdict | Reason |
|---|---|---|
| Managed PostgreSQL (Neon/Supabase/Render) | Rejected | High migration cost (ORM dialect changes, tests), network latency |
| Periodic SQLite dump to S3 | Rejected | Data loss between dump intervals |
| JSON/CSV serialization | Rejected | Fragile, doesn't scale, schema drift risk |
| Render paid plan ($7/mo) | Deferred | Valid option but avoidable with Litestream |

## Consequences

- **Zero data loss**: WAL streaming with 1s sync interval
- **Zero cost**: R2 free tier (10GB storage, 10M class B ops/mo)
- **Zero app changes**: Litestream is transparent to SQLite usage
- **Docker image**: ~10MB larger (Litestream binary)
- **Startup**: ~2-5s restore time for typical DB sizes (<50MB)
- **Dependency**: Cloudflare R2 account + API token required
- **Fallback**: If R2 credentials are not set, app starts without
  replication (same behavior as before this change)
