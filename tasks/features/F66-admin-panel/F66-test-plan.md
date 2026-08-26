# F66 Admin Panel -- Test Plan

**Feature:** F66 (Admin Panel)
**Created:** 2026-08-26
**Tasks covered:** T01 (backend), T02 (admin page), T03 (guard/routing/nav), T04 (i18n)

---

## 1. Unit Tests

Pure function and dependency tests. Backend: pytest. Frontend: Vitest.

### Backend

| # | Test case | Expected outcome |
|---|-----------|------------------|
| U01 | `require_admin` with `is_admin=True` user | Returns the user object, no exception |
| U02 | `require_admin` with `is_admin=False` user | Raises `HTTPException(403)` with detail "Admin access required" |
| U03 | `CreditAdjustRequest(amount=10, reason="bonus")` | Valid schema, fields accessible |
| U04 | `CreditAdjustRequest(amount=-5, reason=None)` | Valid schema, reason defaults to None |
| U05 | `CreditAdjustRequest(amount=0)` | Valid schema (zero grant is a no-op grant path) |
| U06 | `CreditAdjustRequest(reason="x" * 201)` | Pydantic `ValidationError` (max_length=200) |
| U07 | `AdminUserRow` with all fields | Serializes correctly, `credit_balance` is int |
| U08 | `AdminDashboardResponse` with all 8 stat fields | Serializes correctly |
| U09 | `list_users_with_balances` with 3 users, 2 have credits | Returns 3 dicts; user without credit row has `credit_balance=0` |
| U10 | `list_users_with_balances(limit=2, offset=0)` | Returns 2 users + total=3 |
| U11 | `list_users_with_balances(limit=2, offset=2)` | Returns 1 user + total=3 |
| U12 | `get_platform_stats` with seeded data | Returns correct `total_users`, `active_users`, `admin_users`, `total_credits_in_circulation`, `total_credits_granted`, `total_credits_spent`, `total_collection_entries`, `total_scans` |
| U13 | `get_platform_stats` on empty DB | Returns all zeros |

### Frontend

| # | Test case | Expected outcome |
|---|-----------|------------------|
| U14 | `fetchAdminUsers` calls `apiGet` with correct URL and params | Called with `"/api/v1/admin/users"`, `{ limit: "50", offset: "0" }` |
| U15 | `adjustUserCredits(1, 10, "bonus")` calls `apiPatch` | Called with `"/api/v1/admin/users/1/credits"`, `{ amount: 10, reason: "bonus" }` |
| U16 | `fetchAdminDashboard` calls `apiGet` with correct URL | Called with `"/api/v1/admin/dashboard"` |

---

## 2. Integration Tests

API endpoint tests using `TestClient` with dependency overrides. Follow existing pattern from `tests/api/test_credits_router.py`.

**Fixtures needed:**
- `admin_user`: `_make_user(is_admin=True)` with DB row
- `regular_user`: `_make_user(is_admin=False)` with DB row
- `admin_client`: TestClient with admin router, `get_current_user` overridden to admin
- `user_client`: TestClient with admin router, `get_current_user` overridden to regular user
- `noauth_client`: TestClient with admin router, NO `get_current_user` override

### GET /admin/users

| # | Test case | Expected outcome |
|---|-----------|------------------|
| I01 | Admin calls `GET /admin/users` | 200, response `data` is list of user dicts with `credit_balance` |
| I02 | Response includes `id`, `email`, `display_name`, `is_admin`, `is_active`, `credit_balance`, `created_at` | All fields present per user |
| I03 | User without `credit_balances` row | `credit_balance=0` in response |
| I04 | `?limit=1&offset=0` with 3 users | Returns 1 user, `meta.total=3` |
| I05 | `?limit=1&offset=2` | Returns 1 user (third) |
| I06 | `?limit=0` | 422 (ge=1 validation) |
| I07 | `?limit=201` | 422 (le=200 validation) |
| I08 | `?offset=-1` | 422 (ge=0 validation) |

### PATCH /admin/users/{id}/credits

| # | Test case | Expected outcome |
|---|-----------|------------------|
| I09 | `amount=10` on user with balance=0 | 200, `new_balance=10`, `amount_applied=10` |
| I10 | `amount=-5` on user with balance=10 | 200, `new_balance=5`, `amount_applied=-5` |
| I11 | `amount=-999` on user with balance=10 | 200, `new_balance=0`, `amount_applied=-999` (clamped deduction) |
| I12 | `amount=0` | 200, balance unchanged (grant of 0) |
| I13 | `user_id=99999` (nonexistent) | 404, "User not found" |
| I14 | Body includes `reason="admin bonus"` | 200, transaction recorded with reason |
| I15 | Body omits `reason` | 200, reason defaults to "admin_adjust" |
| I16 | Credit transaction has `reference_id="admin:{admin_id}"` | Verify via repo query |

### GET /admin/dashboard

| # | Test case | Expected outcome |
|---|-----------|------------------|
| I17 | Admin calls with seeded data | 200, all 8 stat fields with correct values |
| I18 | Empty DB (only admin user) | 200, `total_users=1`, rest mostly zeros |

### Auth on /auth/me

| # | Test case | Expected outcome |
|---|-----------|------------------|
| I19 | `GET /auth/me` for admin user | Response includes `is_admin: true` |
| I20 | `GET /auth/me` for regular user | Response includes `is_admin: false` |

### Auth/Authz enforcement (all 3 admin endpoints)

| # | Test case | Expected outcome |
|---|-----------|------------------|
| I21 | Regular user calls `GET /admin/users` | 403 |
| I22 | Regular user calls `PATCH /admin/users/{id}/credits` | 403 |
| I23 | Regular user calls `GET /admin/dashboard` | 403 |
| I24 | Unauthenticated call to `GET /admin/users` | 401 |
| I25 | Unauthenticated call to `PATCH /admin/users/{id}/credits` | 401 |
| I26 | Unauthenticated call to `GET /admin/dashboard` | 401 |

---

## 3. Component Tests

React component tests using Vitest + React Testing Library. Mock API calls via `vi.mock`.

### AdminRoute (frontend/src/components/AdminRoute.tsx)

Follow the pattern from `frontend/tests/components/ProtectedRoute.test.tsx` -- render inside `MemoryRouter` with `AuthContext.Provider`.

| # | Test case | Expected outcome |
|---|-----------|------------------|
| C01 | User is admin (`is_admin=true`, `isAuthenticated=true`) | Children rendered |
| C02 | User is authenticated but not admin | Navigates to `/` |
| C03 | User is not authenticated | Navigates to `/login` |
| C04 | Auth `loading=true` | Shows loading spinner ("Checking access...") |
| C05 | `user` is null but `isAuthenticated=false` | Navigates to `/login` |

### AdminPanel -- Users Tab (frontend/src/pages/AdminPanel.tsx)

| # | Test case | Expected outcome |
|---|-----------|------------------|
| C06 | Renders user table with mock user data | Table shows name, email, admin badge, balance, actions columns |
| C07 | User with `credit_balance=0` | Shows "0" in balance column |
| C08 | User with `is_admin=true` | Shows admin badge |
| C09 | Click "Adjust Credits" button on a user row | Opens credit adjustment input/modal |
| C10 | Enter amount=10, click "Apply" | Calls `adjustUserCredits(userId, 10, reason)` |
| C11 | Enter amount=-5, optional reason, click "Apply" | Calls `adjustUserCredits(userId, -5, reason)` |
| C12 | Successful credit adjustment | User list re-fetched, success message shown |
| C13 | Failed credit adjustment (API error) | Error message displayed |
| C14 | Click "Cancel" in credit adjustment | Modal/input closes, no API call |
| C15 | Loading state | Shows spinner |
| C16 | Empty user list | Shows "No users found" message |
| C17 | Pagination: click "Next" | Calls `fetchAdminUsers` with `offset` incremented by `limit` |
| C18 | Pagination: click "Previous" on first page | Previous button disabled |

### AdminPanel -- Dashboard Tab

| # | Test case | Expected outcome |
|---|-----------|------------------|
| C19 | Click Dashboard tab | Dashboard stats rendered |
| C20 | Renders 8 KPI cards with mock data | Total Users, Active Users, Admin Users, Credits in Circulation, Credits Granted, Credits Spent, Collection Entries, Total Scans |
| C21 | Loading state | Shows spinner |
| C22 | Error state | Shows error message |

### Layout Nav Conditional

| # | Test case | Expected outcome |
|---|-----------|------------------|
| C23 | Admin user renders nav | "Admin Panel" link visible |
| C24 | Non-admin user renders nav | "Admin Panel" link NOT visible |
| C25 | Admin user renders nav | "Liga Status" link visible |
| C26 | Non-admin user renders nav | "Liga Status" link NOT visible |
| C27 | Unauthenticated user renders nav | Neither admin link visible |

---

## 4. E2E Scenarios

Key user flows described as step-by-step scenarios. Can be implemented as integration tests or manual test scripts.

### E2E-01: Admin views users and grants credits

1. Admin logs in.
2. Admin clicks "Admin Panel" in sidebar.
3. Admin sees user table with all registered users and their balances.
4. Admin clicks "Adjust Credits" on a user with balance=5.
5. Admin enters amount=20, reason="reward".
6. Admin clicks "Apply".
7. Table refreshes; user now shows balance=25.
8. Admin switches to Dashboard tab; "Credits in Circulation" reflects the increase.

### E2E-02: Admin revokes credits

1. Admin views user table; user has balance=15.
2. Admin clicks "Adjust Credits", enters amount=-10, reason="penalty".
3. Clicks "Apply".
4. User balance now shows 5.

### E2E-03: Non-admin user is blocked

1. Regular user logs in.
2. Sidebar does NOT show "Admin Panel" link.
3. User manually navigates to `/admin`.
4. Frontend redirects to `/`.
5. User calls `GET /api/v1/admin/users` directly (e.g., via curl).
6. Backend returns 403.

### E2E-04: Unauthenticated user is blocked

1. User is not logged in.
2. User navigates to `/admin`.
3. Frontend redirects to `/login`.
4. User calls `GET /api/v1/admin/users` without token.
5. Backend returns 401.

---

## 5. Edge Cases

| # | Scenario | Expected outcome |
|---|----------|------------------|
| EC01 | Grant amount=0 | 200, balance unchanged, transaction recorded with amount=0 |
| EC02 | Revoke more than balance (`amount=-999`, balance=3) | Balance clamped to 0, `actual_deduct=3` |
| EC03 | Revoke when balance is already 0 (`amount=-5`, balance=0) | Balance stays 0, no deduction made |
| EC04 | Admin adjusts own credits | Allowed (no self-grant restriction in spec) |
| EC05 | Very large grant (`amount=999999`) | Succeeds (no upper cap in spec) |
| EC06 | `reason` at exactly 200 chars | Accepted |
| EC07 | `reason` at 201 chars | 422 validation error |
| EC08 | `amount` is not an integer (e.g., 10.5) | 422 validation error |
| EC09 | Pagination: `offset` exceeds total users | Returns empty list, `total` still correct |
| EC10 | Two admins adjust same user concurrently | Both succeed; final balance reflects both changes (last-write-wins on balance) |
| EC11 | `display_name` is null | Table shows email as fallback name |
| EC12 | User with `is_active=false` | Still appears in admin user list |

---

## 6. Security Tests

| # | Test case | Expected outcome |
|---|-----------|------------------|
| S01 | `GET /admin/users` without `Authorization` header | 401 |
| S02 | `GET /admin/users` with expired JWT | 401 |
| S03 | `GET /admin/users` with valid JWT but `is_admin=false` | 403 |
| S04 | `PATCH /admin/users/{id}/credits` without auth | 401 |
| S05 | `PATCH /admin/users/{id}/credits` with non-admin JWT | 403 |
| S06 | `GET /admin/dashboard` without auth | 401 |
| S07 | `GET /admin/dashboard` with non-admin JWT | 403 |
| S08 | IDOR: non-admin tries `PATCH /admin/users/{other_id}/credits` | 403 (blocked by `require_admin`, not IDOR-specific) |
| S09 | Tampered JWT with `is_admin` claim injected | 401 or 403 (`is_admin` comes from DB, not JWT claims) |
| S10 | API key auth (non-admin) on admin endpoints | 403 (API key users respect `is_admin` from DB) |
| S11 | Frontend `AdminRoute` with spoofed `user.is_admin=true` in context but backend rejects | API calls return 403; frontend shows error |
| S12 | SQL injection in `reason` field | Sanitized by SQLAlchemy parameterized queries; no injection |

---

## 7. Regression Tests

Ensure existing credit and auth flows are unaffected by F66 changes.

| # | Test case | Expected outcome |
|---|-----------|------------------|
| R01 | `GET /credits/balance` still works for regular users | 200, correct balance |
| R02 | `POST /credits/claim-bonus` still works for regular users | 200, bonus granted (if eligible) |
| R03 | `GET /credits/history` still works for regular users | 200, transaction list |
| R04 | Admin user can still use regular credit endpoints | 200 (admin bypass intact) |
| R05 | `GET /auth/me` still returns all existing fields | `id`, `email`, `display_name`, `preferred_currency`, etc. all present |
| R06 | `GET /auth/me` now includes `is_admin` | Field present (new), does not break existing consumers |
| R07 | `PATCH /auth/me/preferences` still works | 200, preferences updated, response now includes `is_admin` |
| R08 | `ProtectedRoute` still works for non-admin protected pages | `/collection`, `/decks`, etc. accessible to regular authenticated users |
| R09 | Credit deduction on refresh (1 credit) still works | Not affected by admin credit adjust code |
| R10 | Credit deduction on scan (5 credits) still works | Not affected by admin credit adjust code |
| R11 | Existing nav items for non-admin users unchanged | All current links still visible and functional |
| R12 | `useCredits` hook still returns `isAdmin` correctly | Hook reads from `/credits/balance`, unaffected by `/auth/me` changes |
| R13 | Frontend `UserProfile` type backward-compatible | Adding `is_admin` field does not break existing destructuring |
| R14 | Existing i18n keys (especially `admin.ligaStatus.*`) preserved | No key collisions or overwrites |

---

## Test File Locations (Recommended)

**Backend:**
- `tests/api/test_admin_router.py` -- integration tests for all 3 admin endpoints + auth enforcement (I01--I26)
- `tests/api/test_admin_deps.py` -- unit tests for `require_admin` dependency (U01--U02)
- `tests/api/test_admin_schemas.py` -- schema validation tests (U03--U08)
- `tests/database/test_admin_repo.py` -- repository method tests (U09--U13)
- `tests/api/test_auth_router.py` -- extend existing with is_admin regression (I19--I20, R05--R07)

**Frontend:**
- `frontend/tests/components/AdminRoute.test.tsx` -- guard component tests (C01--C05)
- `frontend/tests/pages/AdminPanel.test.tsx` -- page component tests (C06--C22)
- `frontend/tests/components/Layout.test.tsx` -- extend existing with nav conditional tests (C23--C27)
- `frontend/tests/api/admin.test.ts` -- API client function tests (U14--U16)

**Estimated new test count:** ~70 backend + ~30 frontend = ~100 new tests
