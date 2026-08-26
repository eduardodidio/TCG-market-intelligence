# F66 Admin Panel -- Readiness Report

**Date:** 2026-08-26
**Auditor:** Readiness Agent
**Verdict: READY**

No blocking issues found. All tasks have clear acceptance criteria, all referenced
files exist with expected interfaces, no file conflicts within waves, and
dependencies are correctly ordered.

---

## Checklist

### 1. Acceptance Criteria

| Task | Has Criteria | Count | Notes |
|------|-------------|-------|-------|
| T01  | Yes         | 12    | Covers require_admin, all 3 endpoints, /auth/me fix, 401/403 |
| T02  | Yes         | 7     | Covers user table, dashboard tab, pagination, i18n t() usage |
| T03  | Yes         | 9     | Covers AdminRoute guard, routing, nav filtering, UserProfile type |
| T04  | Yes         | 5     | Covers t() usage, both locales, key preservation |

### 2. Referenced Files Exist

| File | Exists | Expected Interface | Verified |
|------|--------|--------------------|----------|
| `src/database/models.py` -- UserRow.is_admin | Yes | `Mapped[int]`, default=0 (line 207) | OK |
| `src/domain/models.py` -- User.is_admin | Yes | `bool`, default=False (line 453) | OK |
| `src/credits/service.py` -- CreditService | Yes | `grant()`, `deduct()`, `get_balance()` all present | OK |
| `src/api/deps.py` -- get_current_user | Yes | Re-exported from `src.auth.dependencies` (line 85) | OK |
| `src/api/deps.py` -- get_credit_service | Yes | Returns `CreditService(repo)` (line 77) | OK |
| `src/api/deps.py` -- get_db | Yes | Yields `Repository` (line 24) | OK |
| `src/api/routers/auth.py` -- /auth/me | Yes | `get_me()` builds `UserProfile` but omits `is_admin` (line 89-98) | Confirmed -- T01 fix needed |
| `src/api/schemas/auth.py` -- UserProfile | Yes | Already has `is_admin: bool = False` (line 38) | OK -- schema ready, endpoint just needs to pass it |
| `src/api/schemas/envelope.py` -- success_response | Yes | Accepts `**meta_kwargs` (total, offset) | OK |
| `src/api/app.py` -- create_app | Yes | Router registration pattern confirmed (lines 166-190) | OK |
| `src/database/repository.py` -- get_user_by_id | Yes | Returns `UserRow \| None` (line 1434) | OK |
| `src/auth/dependencies.py` -- is_admin mapping | Yes | `is_admin=bool(getattr(user_row, "is_admin", 0))` (lines 62, 97) | OK |
| `frontend/src/api/auth.ts` -- UserProfile | Yes | Missing `is_admin` field (line 10-18) | Confirmed -- T03 fix needed |
| `frontend/src/api/client.ts` -- apiGet, apiPatch | Yes | Both exported with auth headers | OK |
| `frontend/src/contexts/AuthContext.tsx` | Yes | Uses `UserProfile` from auth.ts, exposes `user` | OK |
| `frontend/src/hooks/useAuth.ts` | Yes | Exists | OK |
| `frontend/src/components/ProtectedRoute.tsx` | Yes | Pattern confirmed for AdminRoute reference | OK |
| `frontend/src/components/LoadingSpinner.tsx` | Yes | Exists (used in AdminRoute) | OK |
| `frontend/src/components/Layout.tsx` -- NAV_ITEMS | Yes | Array with `requiresAuth` flag, `as const` (line 14-28) | OK |
| `frontend/src/App.tsx` -- /admin/liga-status route | Yes | Uses `ProtectedRoute` (line 311) | Confirmed -- T03 will change to AdminRoute |
| `frontend/src/pages/AdminLigaStatus.tsx` | Yes | Existing admin page pattern with KpiCard, pagination | OK |
| `frontend/src/i18n/locales/en.json` | Yes | Has existing `admin.ligaStatus.*` keys | OK |
| `frontend/src/i18n/locales/pt-BR.json` | Yes | Has existing `admin.ligaStatus.*` keys | OK |

### 3. No Same-Wave File Conflicts

| Wave | Tasks | Files Modified | Conflict |
|------|-------|----------------|----------|
| 0    | T01   | deps.py, app.py, auth.py (router), repository.py + creates admin.py, schemas/admin.py | N/A (single task) |
| 1    | T02, T03 | T02: creates AdminPanel.tsx, api/admin.ts (modifies none). T03: creates AdminRoute.tsx, modifies auth.ts, App.tsx, Layout.tsx | **No overlap** |
| 2    | T04   | en.json, pt-BR.json | N/A (single task) |

### 4. Wave Dependencies Correct

- **Wave 0 (T01)**: No dependencies. Ships backend first (require_admin, endpoints, /auth/me fix).
- **Wave 1 (T02, T03)**: Both depend on T01. T02 needs the admin API endpoints. T03 needs `is_admin` on `/auth/me` response. T02 and T03 are independent of each other. **Correct.**
- **Wave 2 (T04)**: Depends on T02 and T03. i18n keys are additive to locale files; the `t()` calls in AdminPanel (T02) need the keys from T04. **Correct.**

### 5. Infrastructure References

- `UserRow.is_admin` (Integer, default=0): Confirmed at `src/database/models.py:207`.
- `User.is_admin` (bool): Confirmed at `src/domain/models.py:453`.
- `get_current_user` maps `is_admin`: Confirmed at `src/auth/dependencies.py:62,97`.
- `CreditService.grant(user_id, amount, reason, reference_id)`: Signature matches T01 usage.
- `CreditService.deduct(user_id, cost, reason, reference_id)`: Signature matches T01 usage.
- `CreditService.get_balance(user_id)` returns `CreditBalance` with `.balance` attr: Confirmed.
- `UserProfile` Pydantic schema already has `is_admin: bool = False`: Confirmed at `src/api/schemas/auth.py:38`. The backend schema is ready; only the `get_me` endpoint needs to pass the field.
- `success_response(data=..., total=..., offset=...)` pattern: Confirmed via `**meta_kwargs`.

---

## Observations (non-blocking)

1. **F66-README states "Floor check is already in CreditService"** -- This is slightly inaccurate. `CreditService.grant()` does NOT floor-check; only `deduct()` raises `InsufficientCreditsError`. However, T01's `adjust_credits` endpoint correctly handles this by clamping revocation amounts before calling `deduct()`, so no issue in practice.

2. **`/auth/me` preferences endpoint** also omits `is_admin` (line 122-131 of auth.py). T01 correctly identifies both `get_me` and `update_preferences` need the fix.

3. **Frontend `UserProfile`** in `auth.ts` is also missing `preferred_currency` (not related to F66 but noted). T03 only adds `is_admin`, which is sufficient for this feature.

4. **Layout.tsx NAV_ITEMS uses `as const`**. T03 notes this may need changing to a typed array to support `requiresAdmin?: boolean`. Developer should handle this during implementation.
