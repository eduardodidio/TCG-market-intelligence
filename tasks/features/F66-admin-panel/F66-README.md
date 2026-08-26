# F66 — Admin Panel

**Status:** planned
**Created:** 2026-08-26
**Priority:** P1 (enables credit management)
**Wave Group:** 2 (depends on F65 — credit system must exist first)

## Summary

Create an admin area where administrators (is_admin=1) can view all users,
manage their credit balances (grant/revoke treasure tokens), and see platform
statistics. Admins can grant credits to themselves. Protected by admin-only
middleware.

## Acceptance Criteria

1. `require_admin` dependency that checks `is_admin=1` (returns 403 otherwise)
2. GET /admin/users — list all users with credit balances (paginated)
3. PATCH /admin/users/{id}/credits — add/subtract credits for any user
4. GET /admin/dashboard — platform stats (total users, scans, cards, credits issued)
5. Frontend /admin page with user list + credit management
6. Admin can grant credits to themselves
7. Navigation: "Admin" link in sidebar (visible only to admins)
8. Non-admin users get 403 on all /admin/* endpoints

## Architecture Decisions

- Simple `is_admin` flag (no RBAC roles) — sufficient for current scale
- Admin can grant negative amounts (revoke) — enables corrections
- No credit cap — admin grants are unlimited
- Admin panel is a single page with tabs (Users, Dashboard)

## Waves

| Wave | Tasks | Description |
|------|-------|-------------|
| 0    | T01   | Admin middleware + admin API router |
| 1    | T02   | Frontend admin page + user credit management |

## Tasks

- **T01** (Wave 0): Backend admin router with user list + credit management + dashboard stats
- **T02** (Wave 1): Frontend admin page with user table and credit grant actions
