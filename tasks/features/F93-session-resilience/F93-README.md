# F93 — Session Resilience

**Status:** planned
**Created:** 2026-08-30
**Priority:** High

## Problem

Two related issues with frontend session management:

1. **Stale data after push-db**: When the backend DB is restored via `/db/restore`, the frontend React state/cache holds stale data. User must manually logout and login to see updated collection.

2. **No graceful auth expiry**: When JWT expires (24h), API calls return 401 and `handleUnauthorized()` in `client.ts` immediately clears tokens and redirects to `/login`. The refresh token (30d) is never used for automatic renewal during normal API calls — only on initial mount in AuthContext.

## Solution

- Add **silent token refresh** on 401 responses in `client.ts` (use refresh token before giving up)
- Add **automatic redirect to login** when both tokens are expired (already works, just needs to be graceful)
- Add **`storage` event listener** in AuthContext to sync auth state when tokens change (e.g., another tab logs out)
- Add **`data-version` polling** or a lightweight mechanism to detect backend data changes and trigger refetch

## Architecture

- **No new dependencies**
- **No backend changes** (refresh endpoint already exists at `POST /api/v1/auth/refresh`)
- **Frontend-only** changes in 4 files: `client.ts`, `AuthContext.tsx`, `useApi.ts`, and a new `useDataVersion` hook

## Waves

| Wave | Tasks | Description |
|------|-------|-------------|
| 0 | T01, T02 | Core: silent refresh interceptor + auth state sync |
| 1 | T03, T04 | Data freshness: refetch on focus + storage sync |

## Files Changed

- `frontend/src/api/client.ts` — retry with refresh on 401
- `frontend/src/contexts/AuthContext.tsx` — storage event listener, expose refreshSession()
- `frontend/src/hooks/useApi.ts` — refetch on window focus
- `frontend/src/hooks/useAuthRefresh.ts` — (new) silent refresh utility
