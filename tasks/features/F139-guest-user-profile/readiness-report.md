# Readiness Report: F139

**Verdict:** READY
**Audited at:** 2026-09-18

## Checklist

| # | Check | T01 | T02 | T03 |
|---|-------|-----|-----|-----|
| 1 | User Story | pass | pass | pass |
| 2 | Dev Notes with file paths | pass | pass | pass |
| 3 | Testing with concrete scenarios | pass | pass | pass |
| 4 | Acceptance Criteria | pass | pass | pass |
| 5 | Wave assignment matches README | pass (Wave 0) | pass (Wave 1) | pass (Wave 1) |
| 6 | Dependencies correctly declared | pass (none) | pass (T01) | pass (T01) |
| 7 | File conflicts in same Wave | n/a (solo) | pass | pass |

## Wave File Conflict Analysis

**Wave 0 (T01 only):** No conflict possible -- single task.

**Wave 1 (T02 + T03):**
- T02 touches: `src/cli/main.py`
- T03 touches: `frontend/src/contexts/AuthContext.tsx`, `frontend/src/hooks/useAuth.ts`, `frontend/src/api/auth.ts`, `frontend/src/components/Layout.tsx`, `frontend/src/components/BetaRoute.tsx` (new), `frontend/src/App.tsx`, `frontend/src/i18n/locales/en.json`, `frontend/src/i18n/locales/pt-BR.json`
- **No overlap** -- T02 is backend-only CLI, T03 is frontend-only. Safe to parallelize.

**Cross-Wave overlap (T01 -> T03):** Both list `frontend/src/api/auth.ts`. Not a conflict -- T01 is Wave 0 and completes before T03 starts. T03 explicitly notes "(if not done in T01)", correctly anticipating this.

## Findings

### Verified against codebase

1. **UserRow model** (`src/database/models.py` line 213): Confirmed -- no `role` column exists. T01's instruction to add after `is_admin` is accurate.

2. **UserProfile schema** (`src/api/schemas/auth.py` line 29): Confirmed -- no `role` field. T01 correctly targets this file.

3. **SEED_USERS** (`src/cli/main.py` line 784): Confirmed -- single-entry list with admin user only. T02's approach to add a second entry is valid. Collection reassignment logic (line 824) targets `SEED_USERS[0]`, so the guest (index 1) will not be the reassignment target. T02's note about this is accurate.

4. **AuthContext** (`frontend/src/contexts/AuthContext.tsx` line 24): Confirmed -- `AuthContextValue` interface exists. T03 correctly identifies the need to add `hasBetaAccess`.

5. **useAuth hook** (`frontend/src/hooks/useAuth.ts`): Confirmed -- exists as a separate file. T03's file list includes it, correct since the return type changes with `AuthContextValue`.

6. **ProtectedRoute** (`frontend/src/components/ProtectedRoute.tsx`): Confirmed -- T03's BetaRoute follows the same structural pattern. No existing BetaRoute component exists.

7. **Layout.tsx beta section** (lines 304-331): Confirmed -- beta nav items render in a disclosure section with `visibleBetaItems.map()`. T03's instructions to conditionally render as `<span>` vs `<Link>` align with the actual code structure.

8. **App.tsx beta routes**: Confirmed -- routes for `/market`, `/market/trending`, `/banlist`, `/banlist/history`, `/decks`, `/decks/ranking`, `/decks/build`, `/decks/evaluate`, `/marketplace`, `/trade-matches`, `/evaluations`, `/achievements` all exist. T03 lists 12 beta routes, which matches.

9. **i18n files**: Both `en.json` and `pt-BR.json` exist at the expected paths.

### Advisory notes (non-blocking)

**A1 -- Duplicate UserProfile type in `frontend/src/types/api.ts`:**
Line 419 has a second `UserProfile` interface without `role` (also missing `is_admin` and `must_change_password`). The auth flow imports from `frontend/src/api/auth.ts`, so the duplicate appears stale/secondary. Developer should consider adding `role` there too or removing the duplicate. Non-blocking since auth flow uses the correct file.

**A2 -- Route architecture nuance for public beta routes:**
T03 notes that some beta routes (market, banlist) are currently public while others require auth. However, examining `App.tsx`, these routes are nested under a `<ProtectedRoute><Layout /></ProtectedRoute>` parent wrapper, meaning they already require authentication. T03 acknowledges this tension (lines 97-100) and the developer should decide whether BetaRoute only adds guest-blocking on top of existing auth (simpler) or also restructures public access. Non-blocking -- option (a) is straightforward and the AC can be clarified during development.

**A3 -- `/decks/evaluate` is a redirect, not a page:**
`App.tsx` line 355 shows `/decks/evaluate` as `<Navigate to="/decks?evaluate=true" replace />`. Wrapping with `<BetaRoute>` works since the redirect target `/decks` is also wrapped. Just awareness for the developer.

**A4 -- Toast infrastructure:**
T03 mentions reusing existing toast infrastructure or creating a lightweight `showToast()`. The project has `UndoToast` (a specialized component) but no generic toast utility. Developer will need to implement a simple toast mechanism. Non-blocking -- the task acknowledges this decision point.

**A5 -- T01 migration approach:**
T01 proposes `ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'admin'`. Safe for both SQLite and PostgreSQL (Neon). The idempotency check should use `information_schema.columns` for PostgreSQL or `pragma_table_info` for SQLite. T01's acceptance criteria covers this.

## Blocking issues

- (none)
