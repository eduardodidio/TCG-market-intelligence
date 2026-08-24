# F56 — Auth Hardening & Login UX

**Status:** done
**Priority:** high
**Depends on:** none

## Summary

Fix seed user credentials, redirect unauthenticated users to login page,
and make persistent sessions the default behavior.

## Tasks

| Task | Wave | Description |
|------|------|-------------|
| F56-T01 | 0 | Fix seed user password & default redirect |
| F56-T02 | 0 | Persistent session (long-lived JWT) |

## Wave Plan

- **Wave 0** (all tasks parallel — no dependencies between them):
  - T01: backend seed password + frontend default redirect
  - T02: JWT expiry extension + remove manual logout-on-close

## Acceptance Criteria

1. `seed-users` CLI sets password `mudar@123` for eduardorutkoskididio@gmail.com
2. Unauthenticated users landing on `/` are redirected to `/login`
3. After login, user stays logged in across browser restarts (no session expiry on close)
4. Login with `eduardorutkoskididio@gmail.com` / `mudar@123` works end-to-end
