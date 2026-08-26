# F66 -- Admin Panel

**Status:** planned
**Created:** 2026-08-26
**Priority:** P1 (enables credit management, platform visibility)

## Summary

Create an admin area where administrators (`is_admin=1`) can view all users,
manage their credit balances (grant/revoke treasure tokens), and see platform
statistics. Protected by a `require_admin` FastAPI dependency that returns 403
for non-admin users. Frontend gets an `/admin` route with user table, credit
adjustment, and dashboard stats, guarded by an `AdminRoute` component. The
sidebar shows the "Admin" link only for admin users.

## Pre-existing Infrastructure (DO NOT recreate)

- `UserRow.is_admin` (Integer, default=0) -- already on DB model (F65)
- `User.is_admin` (bool) -- already on domain model (F65)
- `get_current_user()` -- already maps `is_admin` from DB row (F65)
- `UserProfile` Pydantic schema -- already has `is_admin: bool = False` field
- `CreditService` -- already has `grant()`, `deduct()`, `get_balance()` methods
- `useCredits` hook -- already exposes `isAdmin` from `/credits/balance`
- Frontend `UserProfile` in `auth.ts` -- does NOT have `is_admin` (needs adding)
- `/auth/me` endpoint -- does NOT include `is_admin` in response (needs fixing)

## Acceptance Criteria

1. `require_admin` FastAPI dependency checks `user.is_admin`, raises 403 if false
2. `GET /admin/users` returns paginated user list with credit balances (admin only)
3. `PATCH /admin/users/{id}/credits` grants or revokes credits (admin only)
4. `GET /admin/dashboard` returns platform stats (admin only)
5. Frontend `/admin` page with user table and credit grant/revoke per user
6. Frontend `/admin` page with dashboard stats tab
7. `AdminRoute` guard component redirects non-admin to `/`
8. Sidebar shows "Admin" link only when `user.is_admin` is true
9. All admin endpoints return 401 without auth, 403 without admin
10. i18n keys for EN and PT-BR

## Architecture Decisions

- **`require_admin` as FastAPI `Depends`**: Chains on `get_current_user`, single
  point of admin enforcement. Reusable across future admin endpoints.
- **Credit adjust via CreditService.grant()**: Negative amounts for revocation.
  Floor check (balance cannot go below 0) is already in CreditService.
- **`is_admin` on `/auth/me`**: Currently missing from the response. Must be
  added so the frontend `AuthContext` knows admin status at login time, not
  only after `/credits/balance` loads.
- **AdminRoute vs extending ProtectedRoute**: Separate component is clearer.
  AdminRoute wraps ProtectedRoute internally.
- **Nav filtering**: Add `requiresAdmin` flag to NAV_ITEMS, filter by
  `user?.is_admin` in Layout.

## Waves

| Wave | Tasks | Description |
|------|-------|-------------|
| 0    | T01   | `require_admin` dep + admin API router + schemas + repo methods |
| 1    | T02, T03 | Frontend: AdminRoute + admin page (parallel: page vs nav/route wiring) |
| 2    | T04   | i18n keys + tests cleanup |

## Tasks

- **T01** (Wave 0): Backend -- `require_admin` dependency, admin router (users, credits, dashboard), schemas, repository methods
- **T02** (Wave 1): Frontend -- AdminPanel page with user table + credit adjust + dashboard stats tab
- **T03** (Wave 1): Frontend -- AdminRoute guard, App.tsx route, Layout.tsx nav conditional, `/auth/me` `is_admin` fix
- **T04** (Wave 2): i18n keys (EN + PT-BR) for all admin UI strings

## Diagrams

- `docs/diagrams/F66-architecture.mmd` -- admin API flow: require_admin, router, service, repo
- `docs/diagrams/F66-journey.mmd` -- admin user journey: view users, grant credits, view stats
