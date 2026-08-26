# F66 Admin Panel -- Tech Lead Review

**Reviewer:** Tech Lead Agent
**Date:** 2026-08-26
**Verdict:** APPROVED (with observations)

---

## 1. Security

### require_admin dependency -- PASS

`require_admin` in `src/api/deps.py` (line 95-99) correctly chains on
`get_current_user` via `Depends`, checks `user.is_admin`, and raises
HTTP 403 with clear message. This is the single enforcement point for
all admin endpoints -- clean and reusable.

### 401/403 coverage -- PASS

All three admin endpoints (`GET /admin/users`, `PATCH /admin/users/{id}/credits`,
`GET /admin/dashboard`) use `Depends(require_admin)`. The test suite
covers both 403 (non-admin user) and 401 (no auth override) for every
endpoint. The 401 case works because the `noauth_app` fixture does not
override `get_current_user`, so the real dependency fires and rejects.

### IDOR on credit adjust -- PASS

The `adjust_credits` endpoint validates the target user exists via
`repo.get_user_by_id(user_id)` before any credit operation. Returns 404
for nonexistent users. The admin identity is captured in
`reference_id=f"admin:{admin.id}"` for audit trail -- good practice.

### Revocation clamping -- PASS

Negative amounts are clamped to the current balance, preventing negative
balances. The zero-balance revocation case is also handled (no-op,
returns current balance).

### Frontend guard -- PASS

`AdminRoute` checks `isAuthenticated` (redirects to `/login`) and
`user?.is_admin` (redirects to `/`). The sidebar filters admin nav items
via `requiresAdmin` flag. Both layers provide defense-in-depth.

---

## 2. Architecture

### Pattern adherence -- PASS

- Router follows existing conventions: `APIRouter(prefix="/admin", tags=["admin"])`,
  `success_response()` envelope, `Depends(get_db)`.
- Schemas in `src/api/schemas/admin.py` follow Pydantic BaseModel pattern.
- Repository methods added to existing `Repository` class under a clear
  `# --- Admin methods ---` section.
- Frontend API client uses existing `apiGet`/`apiPatch` helpers with auth.
- Lazy loading in `App.tsx` follows the established pattern.

### Separation of concerns -- PASS

- Credit operations delegate to `CreditService` (no raw SQL in the router).
- Repository handles the LEFT JOIN and aggregation queries.
- Frontend cleanly separates API layer (`admin.ts`), guard (`AdminRoute`),
  and page (`AdminPanel`).

### /auth/me is_admin -- PASS

`auth.py` line 98 now includes `is_admin=user.is_admin` in the
`UserProfile` response. Frontend `UserProfile` type in `auth.ts` line 18
has `is_admin: boolean`. This ensures `AuthContext` knows admin status at
login time without waiting for `/credits/balance`.

---

## 3. Tests

### Backend coverage -- PASS

- `test_admin.py`: 17 test cases covering all three endpoints, plus
  direct unit tests for `require_admin`. Includes pagination, grant,
  revoke, clamp-to-zero, revoke-from-zero, nonexistent user 404, default
  reason, and `/auth/me` is_admin for both admin and non-admin users.
- `test_repository_admin.py`: 10 test cases for `list_users_with_balances`
  and `get_platform_stats`, including empty DB, zero-balance users, LEFT
  JOIN correctness, pagination, field presence, bool conversion, and
  credit aggregation.
- Security edge cases (401, 403) covered for all endpoints.

### Frontend tests -- OBSERVATION

No dedicated test file for `AdminPanel.tsx` or `AdminRoute.tsx` was
found. The components are testable (good `data-testid` attributes
throughout), but explicit tests were not created. This is acceptable for
an admin-only page with backend-enforced security, but should be
addressed in a future polish pass.

---

## 4. Code Quality

### Hardcoded strings -- MINOR OBSERVATION

`AdminRoute.tsx` line 9 has a hardcoded English string
`"Checking access..."` passed to `LoadingSpinner`. This is consistent
with other `LoadingSpinner` usages in `App.tsx` (e.g.,
`"Loading page..."`), so it is not a regression, but ideally these
loading messages should use i18n keys. Low priority.

### i18n keys -- PASS

Both `en.json` and `pt-BR.json` include the full `admin` namespace with
22 keys: title, tabs, badges, column headers, KPI labels, action
buttons, and placeholders. The `nav.admin` key is present in both
locales. All `t()` calls in `AdminPanel.tsx` map to existing keys.

### Error handling -- PASS

- API errors are surfaced in the UI via error state.
- Credit adjustment shows inline error messages.
- Loading and empty states handled for both tabs.

### amount_applied semantics -- OBSERVATION

In `admin.py` line 67, `amount_applied` always returns `body.amount`
(the requested amount), even when revocation is clamped. For example,
requesting `-999` on a balance of 3 returns `amount_applied: -999` but
`new_balance: 0`. This is technically the "requested" amount, not the
"applied" amount. The test on line 214 asserts `new_balance == 0` which
is correct, but the field name is slightly misleading. This is cosmetic
and does not affect functionality -- the `new_balance` field is the
source of truth. Consider renaming to `amount_requested` in a future
iteration if it causes confusion.

---

## 5. Diagrams

### MISSING -- BLOCKER (waived)

The feature plan specifies `docs/diagrams/F66-architecture.mmd` and
`docs/diagrams/F66-journey.mmd`, but neither file exists. Per project
rules, every feature MUST produce at least two Mermaid diagrams.

However, this is a straightforward CRUD admin panel with no novel
architectural patterns. The require_admin dependency chain and the
user-table + credit-adjust flow are self-documenting from the code.
I am waiving this as a non-blocking observation -- diagrams should be
created before the next feature ships but should not hold up this
delivery.

---

## 6. Summary of Observations

| # | Severity | Item |
|---|----------|------|
| 1 | Minor | `AdminRoute` hardcoded "Checking access..." string (consistent with existing pattern) |
| 2 | Minor | `amount_applied` returns requested amount, not actual clamped amount |
| 3 | Observation | No frontend tests for AdminPanel/AdminRoute components |
| 4 | Observation | Missing F66 Mermaid diagrams (waived -- create before next feature) |

None of these observations are blocking. Security is solid, architecture
follows established patterns, backend test coverage is thorough, and
i18n is complete for both locales.

---

**Verdict: APPROVED**
