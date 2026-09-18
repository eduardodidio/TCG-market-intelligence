# QA Report: F139 — Guest User Profile

**Verdict:** PASSED_WITH_NOTES
**Date:** 2026-09-18

## Test Results

| Suite | Passed | Failed | Notes |
|-------|--------|--------|-------|
| Backend (F139-specific) | 28 | 0 | test_user_role.py (14) + test_seed_users.py (14) |
| Frontend (F139-specific) | 49 | 0 | BetaRoute (7) + Layout (38) + AdminRoute (2) + ProtectedRoute (2) |
| TypeScript | N/A | 3 | Pre-existing errors in TrendingCollectionOnly.test.tsx (unrelated) |

## Acceptance Criteria

### T01 — Backend: role column + schema + API

| Criterion | Status |
|-----------|--------|
| `users` table has `role` column with default "admin" | PASS |
| Existing users default to "admin" | PASS |
| `GET /auth/me` returns `role` field | PASS |
| Column addition is idempotent | PASS |

### T02 — Backend: seed guest user in CLI

| Criterion | Status |
|-----------|--------|
| `seed-users` creates guest@tedhmarket.com.br with role="guest", is_admin=0 | PASS |
| Guest password is "mudar@12345" | PASS |
| Guest receives 10,000 initial credits | PASS |
| Running seed-users twice is idempotent | PASS |
| Collection entries NOT reassigned to guest | PASS |

### T03 — Frontend: beta access control

| Criterion | Status |
|-----------|--------|
| Guest sees Beta Test section in sidebar (visible) | PASS |
| Guest beta items are greyed out and not clickable | PASS |
| Clicking disabled beta item shows toast message | PASS |
| Direct URL navigation shows blocked message | PASS |
| Admin user behavior unchanged | PASS |
| Anonymous users can access public beta routes | PASS |
| i18n keys present for both locales | PASS |

## Documentation

| Doc | Status |
|-----|--------|
| ADR-0013 (guest-user-role-system.md) | PASS |
| F139-architecture.mmd | PASS |
| F139-journey.mmd | PASS |
| README.md updated | PASS |

## Notes

1. **Backend enforcement gap** — Beta restrictions are frontend-only.
   Guest users can still call API endpoints (e.g., deck CRUD) directly.
   Acceptable per ADR-0013 (UX restriction, not security boundary).
   Tracked as follow-up if needed.

2. **Pre-existing TypeScript errors** — 3 errors in
   `TrendingCollectionOnly.test.tsx` are unrelated to F139 (missing
   `preferred_currency` in UserProfile type, tuple type mismatch).

3. **Pre-existing test failure** — `TreasureModal.test.tsx` has 1
   pre-existing failure, unrelated to F139.
