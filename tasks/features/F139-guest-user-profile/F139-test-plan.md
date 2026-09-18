# F139 -- Guest User Profile: Test Plan

**Feature:** F139 -- Guest User Profile
**Date:** 2026-09-18
**Tasks covered:** T01 (role column + schema + API), T02 (seed guest user), T03 (frontend beta access control)

---

## 1. Scope

This test plan covers all changes introduced by F139, which adds a `role`
column to the `users` table and implements a guest user profile with
restricted access to Beta Test features.

### What is being tested

**Backend (T01 + T02):**
- `UserRow` model: new `role` column with `"admin"` default
- `UserProfile` Pydantic schema: new `role` field
- `/auth/me` endpoint: `role` field in response
- Database migration: idempotent `ALTER TABLE` for `role` column (SQLite + PostgreSQL)
- `seed-users` CLI: guest user creation with correct email, password, role, credits, and no collection reassignment

**Frontend (T03):**
- `UserProfile` TypeScript type: `role` field
- `AuthContext`: new `hasBetaAccess` computed property
- `Layout.tsx`: disabled beta nav items for guest users (greyed-out spans + toast on click)
- `BetaRoute` component: new route guard blocking beta routes for guests
- `App.tsx`: 12 beta routes wrapped with `BetaRoute`
- i18n: `beta.blocked` key in both `en.json` and `pt-BR.json`

### What is NOT being tested

- Role-based permission matrix beyond beta access
- Admin panel access restrictions for guest (already handled by `AdminRoute`)
- OAuth guest login
- Shared collection data between users

---

## 2. Unit Tests (Backend)

### 2.1 UserRow Model (`tests/auth/test_user_model.py`)

| # | Test Case | Expected Outcome |
|---|-----------|------------------|
| 1 | `test_user_default_role_is_admin` | `UserRow(email=..., auth_provider=...)` creates with `role == "admin"` |
| 2 | `test_user_role_guest` | `UserRow(..., role="guest")` persists `role == "guest"` correctly |
| 3 | `test_user_role_column_exists` | `inspect(engine).get_columns("users")` includes column named `"role"` |
| 4 | `test_user_role_max_length_20` | Column type is `VARCHAR(20)` / `String(20)` |
| 5 | `test_existing_user_without_role_defaults_to_admin` | A user inserted without explicit `role` reads back as `role == "admin"` |

### 2.2 UserProfile Schema (`tests/api/test_schemas.py` or `tests/auth/test_auth_router.py`)

| # | Test Case | Expected Outcome |
|---|-----------|------------------|
| 6 | `test_user_profile_includes_role_field` | `UserProfile(id=1, email="...", auth_provider="email", is_active=True).role == "admin"` (default) |
| 7 | `test_user_profile_role_guest` | `UserProfile(..., role="guest").role == "guest"` |
| 8 | `test_user_profile_role_serialization` | `UserProfile(..., role="guest").model_dump()` includes `{"role": "guest"}` |

### 2.3 Auth Router -- `/auth/me` role mapping (`tests/auth/test_auth_router.py`)

Follow existing `TestGetMe` pattern. **Important:** the existing `_mock_user_row()` helper must
be updated to include `"role": "admin"` in its defaults dict -- otherwise `MagicMock(spec=UserRow)`
will not have a `role` attribute and the endpoint will fail.

```python
# Update _mock_user_row defaults dict:
defaults = {
    ...,
    "role": "admin",          # <-- ADD THIS
}
```

| # | Test Case | Expected Outcome |
|---|-----------|------------------|
| 9 | `test_get_me_returns_role_admin` | `GET /auth/me` with admin mock user returns `data.role == "admin"` |
| 10 | `test_get_me_returns_role_guest` | `GET /auth/me` with `role="guest"` mock user returns `data.role == "guest"` |
| 11 | `test_get_me_default_role_when_attribute_missing` | Mock user without `role` kwarg defaults to `"admin"` in response |

```python
def test_get_me_returns_role_guest(self):
    mock_repo = MagicMock()
    mock_repo.get_user_by_id.return_value = _mock_user_row(role="guest")
    client = TestClient(_make_app(mock_repo))
    token = create_access_token(user_id=1, email="test@example.com")
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["role"] == "guest"
```

### 2.4 Database Migration (`tests/database/test_role_migration.py`)

| # | Test Case | Expected Outcome |
|---|-----------|------------------|
| 12 | `test_role_column_added_idempotently` | Running the migration helper twice on same DB does not raise an error |
| 13 | `test_role_column_default_value_applied` | After migration, existing rows without `role` have `"admin"` as value |

**Pattern:** Use `tmp_path` SQLite. Create tables, insert a user via raw SQL
(`INSERT INTO users (...) VALUES (...)` without `role`), then call the migration
helper, then read back and assert `role == "admin"`.

### 2.5 Seed Users CLI (`tests/cli/test_seed_users.py`)

Follow the existing `TestSeedUsers` pattern: `CliRunner`, `tmp_path`, `Repository`.

| # | Test Case | Expected Outcome |
|---|-----------|------------------|
| 14 | `test_creates_guest_user` | `seed-users` creates `guest@tedhmarket.com.br` with `role="guest"`, `is_admin=0` |
| 15 | `test_guest_user_display_name` | Guest user has `display_name == "Guest"` |
| 16 | `test_guest_user_password` | Guest password is `mudar@12345` (not the `TCG_SEED_PASSWORD` env var value) |
| 17 | `test_guest_user_initial_credits` | Guest receives 10,000 initial credits |
| 18 | `test_guest_idempotent_second_run` | Running `seed-users` twice does not duplicate; output shows "Skipped (exists)" for guest |
| 19 | `test_guest_existing_updated_to_role_guest` | If guest user exists with `role="admin"`, seed-users corrects to `role="guest"`, `is_admin=0` |
| 20 | `test_collection_not_reassigned_to_guest` | Collection entries reassigned ONLY to admin (first) seed user, never to guest |
| 21 | `test_admin_seed_user_still_created` | Admin user created with `role="admin"`, `is_admin=1` alongside guest |
| 22 | `test_both_users_created_in_single_run` | Single run output contains both emails |

```python
def test_creates_guest_user(self, tmp_path):
    db_path = tmp_path / "test_seed_guest.db"
    db_url = f"sqlite:///{db_path}"
    runner = CliRunner()
    result = runner.invoke(cli, ["seed-users", "--db", db_url])
    assert result.exit_code == 0

    repo = Repository(db_url=db_url)
    guest = repo.get_user_by_email("guest@tedhmarket.com.br")
    assert guest is not None
    assert guest.role == "guest"
    assert guest.is_admin == 0
    assert verify_password("mudar@12345", guest.password_hash)

def test_guest_password_not_env_var(self, tmp_path, monkeypatch):
    db_path = tmp_path / "test_seed_guest_pw.db"
    db_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("TCG_SEED_PASSWORD", "custom-admin-pw")
    runner = CliRunner()
    result = runner.invoke(cli, ["seed-users", "--db", db_url])
    assert result.exit_code == 0

    repo = Repository(db_url=db_url)
    guest = repo.get_user_by_email("guest@tedhmarket.com.br")
    # Guest uses hardcoded password, NOT env var
    assert verify_password("mudar@12345", guest.password_hash)
    assert not verify_password("custom-admin-pw", guest.password_hash)

def test_collection_not_reassigned_to_guest(self, tmp_path):
    db_path = tmp_path / "test_seed_no_guest_reassign.db"
    db_url = f"sqlite:///{db_path}"

    repo = Repository(db_url=db_url)
    with Session(repo.engine) as session:
        session.add(UserCollectionRow(
            user_id="orphan", set_code="mh3",
            collector_number="1", name_en="Test", quantity=1,
        ))
        session.commit()

    runner = CliRunner()
    result = runner.invoke(cli, ["seed-users", "--db", db_url])
    assert result.exit_code == 0

    admin = repo.get_user_by_email("eduardorutkoskididio@gmail.com")
    guest = repo.get_user_by_email("guest@tedhmarket.com.br")
    with Session(repo.engine) as session:
        entries = session.query(UserCollectionRow).all()
        for entry in entries:
            assert entry.user_id == str(admin.id)
            assert entry.user_id != str(guest.id)
```

---

## 3. Unit Tests (Frontend)

### 3.1 UserProfile Type (`frontend/tests/api/auth.test.ts` -- compile check)

| # | Test Case | Expected Outcome |
|---|-----------|------------------|
| 23 | `test_user_profile_type_has_role` | TypeScript compilation succeeds with `role: string` field on `UserProfile` |

### 3.2 AuthContext -- `hasBetaAccess` (`frontend/tests/contexts/AuthContext.test.tsx`)

| # | Test Case | Expected Outcome |
|---|-----------|------------------|
| 24 | `test_hasBetaAccess_true_for_admin_role` | `user.role === "admin"` yields `hasBetaAccess === true` |
| 25 | `test_hasBetaAccess_false_for_guest_role` | `user.role === "guest"` yields `hasBetaAccess === false` |
| 26 | `test_hasBetaAccess_true_when_role_undefined` | `user` without `role` field (backward compat) yields `hasBetaAccess === true` |
| 27 | `test_hasBetaAccess_when_no_user` | `user === null` yields `hasBetaAccess` is falsy (no crash) |

### 3.3 Layout -- Beta Items for Guest (`frontend/tests/components/Layout.test.tsx`)

Add a `mockAuthGuest` fixture to the existing file. All existing fixtures
(`mockAuthAuthenticated`, `mockAuthAdmin`) must be updated to include
`hasBetaAccess: true` (or omit it if the default is `true`). The new guest
fixture must set `hasBetaAccess: false`.

```typescript
const mockAuthGuest: AuthContextValue = {
  user: {
    id: 2,
    email: "guest@tedhmarket.com.br",
    display_name: "Guest",
    avatar_url: null,
    auth_provider: "email",
    preferred_language: null,
    is_active: true,
    is_admin: false,
    role: "guest",
  },
  loading: false,
  error: null,
  isAuthenticated: true,
  hasBetaAccess: false,
  login: vi.fn().mockResolvedValue(null),
  register: vi.fn().mockResolvedValue(null),
  logout: vi.fn().mockResolvedValue(undefined),
  mustChangePassword: false,
  changePassword: vi.fn().mockResolvedValue(null),
};
```

| # | Test Case | Expected Outcome |
|---|-----------|------------------|
| 28 | `test_guest_sees_beta_section_toggle` | Guest user sees "Beta Test" toggle button (section visible) |
| 29 | `test_guest_beta_items_rendered_as_disabled_spans` | Beta expanded: items are `<span>` (not `<a>`) with `opacity-50` + `cursor-not-allowed` |
| 30 | `test_guest_beta_items_not_clickable_links` | Beta items for guest do NOT have `href` attributes |
| 31 | `test_guest_click_disabled_beta_item_shows_toast` | Click disabled beta item: toast appears with blocked message text |
| 32 | `test_admin_beta_items_still_links` | Admin beta items remain `<a>` links (no regression) |
| 33 | `test_admin_beta_items_count_unchanged` | Admin nav link count unchanged (21 with beta expanded) |
| 34 | `test_guest_primary_nav_items_are_links` | Guest primary nav items (Dashboard, Collection, etc.) are `<a>` links |
| 35 | `test_guest_beta_items_visible_when_expanded` | Guest can expand beta; item labels are visible (text present) |

### 3.4 BetaRoute Component (`frontend/tests/components/BetaRoute.test.tsx`)

**NEW file.** Follow `AdminRoute.test.tsx` and `ProtectedRoute.test.tsx` patterns exactly:
`renderWithAuth()` helper, `AuthContext.Provider`, `MemoryRouter` + `Routes`.

```typescript
function renderWithAuth(
  auth: Partial<AuthContextValue>,
  initialPath = "/decks",
) {
  const mockAuth: AuthContextValue = {
    user: null,
    loading: false,
    error: null,
    isAuthenticated: false,
    hasBetaAccess: true,
    login: vi.fn().mockResolvedValue(null),
    register: vi.fn().mockResolvedValue(null),
    logout: vi.fn().mockResolvedValue(undefined),
    mustChangePassword: false,
    changePassword: vi.fn().mockResolvedValue(null),
    ...auth,
  };

  return render(
    <AuthContext.Provider value={mockAuth}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route
            path="/decks"
            element={
              <BetaRoute>
                <div data-testid="beta-content">Beta content</div>
              </BetaRoute>
            }
          />
          <Route
            path="/login"
            element={<div data-testid="login-page">Login Page</div>}
          />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

const adminUser = {
  id: 1,
  email: "admin@example.com",
  display_name: "Admin",
  avatar_url: null,
  auth_provider: "email",
  preferred_language: null,
  is_active: true,
  is_admin: true,
  role: "admin",
};

const guestUser = {
  id: 2,
  email: "guest@tedhmarket.com.br",
  display_name: "Guest",
  avatar_url: null,
  auth_provider: "email",
  preferred_language: null,
  is_active: true,
  is_admin: false,
  role: "guest",
};
```

| # | Test Case | Expected Outcome |
|---|-----------|------------------|
| 36 | `test_renders_children_for_admin_user` | Admin sees child content (`data-testid="beta-content"` present) |
| 37 | `test_renders_blocked_message_for_guest_user` | Guest sees blocked message card (child content absent) |
| 38 | `test_blocked_message_text_matches_i18n_key` | Blocked message contains expected text |
| 39 | `test_redirects_to_login_when_unauthenticated` | Unauthed user on `/decks` redirects to `/login` |
| 40 | `test_shows_loading_spinner_while_auth_loading` | `loading=true`: spinner shown, no content or blocked message |
| 41 | `test_guest_does_not_see_child_content` | Guest: `queryByTestId("beta-content")` returns null |
| 42 | `test_guest_stays_on_same_url` | Guest on `/decks`: no `<Navigate>`, stays on `/decks` showing message card |

### 3.5 i18n Keys (`frontend/tests/i18n/betaBlocked-keys.test.tsx`)

| # | Test Case | Expected Outcome |
|---|-----------|------------------|
| 43 | `test_en_has_beta_blocked_key` | `en.json` has nested key `beta.blocked` with non-empty string |
| 44 | `test_ptBR_has_beta_blocked_key` | `pt-BR.json` has nested key `beta.blocked` with non-empty string |
| 45 | `test_en_and_ptBR_have_same_leaf_key_count` | Both locale files have identical key sets (existing parity check extended) |
| 46 | `test_beta_blocked_pt_br_content` | PT-BR value is `"Esta funcao nao esta habilitada para o perfil atual"` |
| 47 | `test_beta_blocked_en_content` | EN value is `"This feature is not available for the current profile"` |

---

## 4. Integration Tests

### 4.1 API Integration (`tests/auth/test_auth_router.py`)

| # | Test Case | Expected Outcome |
|---|-----------|------------------|
| 48 | `test_auth_me_response_contains_role_field` | `GET /auth/me` JSON response has `"role"` key in `data` |
| 49 | `test_guest_login_returns_role_guest` | Login as guest, `GET /auth/me` returns `role="guest"` |
| 50 | `test_admin_login_returns_role_admin` | Login as admin, `GET /auth/me` returns `role="admin"` |
| 51 | `test_guest_can_access_non_beta_endpoints` | Guest user can `GET /collection` (standard features work) |

### 4.2 CLI Integration (`tests/cli/test_seed_users.py`)

| # | Test Case | Expected Outcome |
|---|-----------|------------------|
| 52 | `test_seed_users_full_flow` | Fresh DB: creates both users, admin=`role="admin"`, guest=`role="guest"`. Second run idempotent. |
| 53 | `test_seed_users_with_existing_collection` | Pre-populated collection reassigned ONLY to admin, not guest. |

### 4.3 Frontend Integration (Vitest + React Testing Library)

| # | Test Case | Expected Outcome |
|---|-----------|------------------|
| 54 | `test_guest_navigates_to_decks_url_sees_blocked` | Guest on `/decks`: BetaRoute renders blocked message, not DecksPage |
| 55 | `test_admin_navigates_to_decks_url_sees_page` | Admin on `/decks`: sees normal page content |
| 56 | `test_guest_sidebar_click_shows_toast_no_navigation` | Guest clicks disabled beta item: toast appears, URL unchanged |

---

## 5. Edge Cases

### 5.1 Backward Compatibility

| # | Test Case | Expected Outcome |
|---|-----------|------------------|
| 57 | `test_existing_users_without_role_column_default_admin` | Users created before F139 get `"admin"` after migration |
| 58 | `test_frontend_handles_missing_role_in_api_response` | If API response omits `role`, frontend treats user as admin (graceful fallback) |
| 59 | `test_mock_user_row_without_role_attribute` | `_mock_user_row()` without `role` kwarg defaults to `"admin"` |
| 60 | `test_existing_layout_tests_pass_with_new_context_shape` | All pre-F139 `Layout.test.tsx` tests pass after `hasBetaAccess` addition to context |

### 5.2 Boundary Conditions

| # | Test Case | Expected Outcome |
|---|-----------|------------------|
| 61 | `test_role_value_case_sensitivity` | `role="Guest"` (capital G) is NOT treated as guest; only lowercase `"guest"` is restricted |
| 62 | `test_role_empty_string` | `role=""` has beta access (not blocked) |
| 63 | `test_role_unknown_value` | `role="viewer"` (unknown) has beta access (only `"guest"` is restricted) |
| 64 | `test_guest_cannot_access_admin_panel` | Guest with `is_admin=0` blocked by existing `AdminRoute` (verify no regression) |
| 65 | `test_guest_accesses_non_beta_routes` | Guest can access `/collection`, `/settings`, `/alerts`, `/catalog` normally |
| 66 | `test_anonymous_user_public_beta_routes` | Anonymous (not logged in) can access `/market`, `/banlist` (public routes) |
| 67 | `test_anonymous_user_auth_required_beta_route` | Anonymous on `/decks` redirected to `/login` |

### 5.3 Error Scenarios

| # | Test Case | Expected Outcome |
|---|-----------|------------------|
| 68 | `test_migration_idempotent_no_error_on_rerun` | `ALTER TABLE` helper safe on second execution |
| 69 | `test_beta_route_with_expired_token` | Guest with expired token redirected to login, not shown blocked message |

---

## 6. Regression Risks

### 6.1 High Risk

| Area | Risk | Mitigation |
|------|------|------------|
| **`_mock_user_row()` in `test_auth_router.py`** | Mock does not include `role` attribute; `/auth/me` mapping will fail if endpoint reads `row.role` on a mock lacking it | Add `"role": "admin"` to `_mock_user_row()` defaults dict. This is the single most likely cause of test failures. |
| **`AuthContextValue` interface** | Adding `hasBetaAccess` field means all existing test mocks must include it or the type check fails | Add `hasBetaAccess: true` to `mockAuthAuthenticated`, `mockAuthAdmin`, and `mockAuthUnauthenticated` in `Layout.test.tsx`. Same for `AdminRoute.test.tsx` and `ProtectedRoute.test.tsx`. |
| **Layout link count assertions** | `Layout.test.tsx` asserts exact `<a>` counts (8 primary, 20 total, 21 admin). If beta items become `<span>` for guests, these counts change. | Existing tests use admin/non-admin mocks (not guest). They should remain green because `hasBetaAccess` defaults to `true`. Guest-specific tests use separate assertions. |
| **`ProtectedRoute` replaced by `BetaRoute`** | If `BetaRoute` wraps beta routes in `App.tsx` but doesn't embed the auth check, unauthenticated users bypass login on auth-required beta routes. | `BetaRoute` MUST check `isAuthenticated` for auth-required routes (embed ProtectedRoute logic or compose both guards). |

### 6.2 Medium Risk

| Area | Risk | Mitigation |
|------|------|------------|
| **`/auth/me` response shape** | Adding `role` field could break API consumers not expecting it | `role` is additive with a default. Existing consumers should ignore unknown fields. |
| **`seed-users` CLI output** | Existing tests assert specific output strings. Adding guest user changes output. | Ensure admin messages unchanged; guest messages are additive. Existing test `test_idempotent_second_run` asserts `"Created" not in result2.output` -- if both users exist, second run should skip both. |
| **JWT payload** | If `role` is embedded in JWT, existing tokens (from before F139) lack the field | Prefer reading `role` from DB via `/auth/me`. If JWT is used, make `role` optional with default `"admin"` in decode logic. |
| **DB migration on Neon (PostgreSQL)** | `ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'admin'` must work on PostgreSQL | Test migration on SQLite (unit tests). Use column-existence check before ALTER to avoid "column already exists" errors. |

### 6.3 Low Risk

| Area | Risk | Mitigation |
|------|------|------------|
| **i18n key parity** | Adding `beta.blocked` to one locale but not the other | Existing `locales.test.ts` checks EN/PT-BR key parity. |
| **Dark mode** | BetaRoute blocked card must support dark theme | Use `dark:` Tailwind variants (`dark:bg-slate-800`, `dark:text-slate-400`). |
| **PWA offline** | Cached pages might show stale UI without role restrictions | ServiceWorker does not cache auth state. |

### 6.4 Existing Test Files to Re-run

These files MUST pass after F139 changes (with mock updates):

| File | Why |
|------|-----|
| `tests/auth/test_auth_router.py` | `_mock_user_row()` updated; `/auth/me` response changed |
| `tests/cli/test_seed_users.py` | Seed logic changed (new user + output messages) |
| `frontend/tests/components/Layout.test.tsx` | `AuthContextValue` interface changed |
| `frontend/tests/components/AdminRoute.test.tsx` | `AuthContextValue` interface changed |
| `frontend/tests/components/ProtectedRoute.test.tsx` | `AuthContextValue` interface changed |
| `frontend/tests/i18n/locales.test.ts` | New i18n keys added |

---

## 7. Test Commands

### Backend

```bash
# Run ALL backend tests (verify no regressions)
pytest tests/ --cov=src --cov-report=term-missing

# Run only F139-related backend tests
pytest tests/auth/test_user_model.py tests/auth/test_auth_router.py tests/cli/test_seed_users.py tests/database/test_role_migration.py -v

# Run only the auth router tests (role in /auth/me)
pytest tests/auth/test_auth_router.py::TestGetMe -v

# Run only the seed-users CLI tests
pytest tests/cli/test_seed_users.py -v

# Lint check
ruff check src/
```

### Frontend

```bash
# Run ALL frontend tests (verify no regressions)
cd frontend && npm test

# Run only F139-related frontend tests
cd frontend && npx vitest run tests/components/BetaRoute.test.tsx tests/components/Layout.test.tsx tests/contexts/AuthContext.test.tsx tests/i18n/locales.test.ts tests/components/AdminRoute.test.tsx tests/components/ProtectedRoute.test.tsx

# Run only BetaRoute tests (new file)
cd frontend && npx vitest run tests/components/BetaRoute.test.tsx

# Run only Layout tests (includes new guest beta item tests)
cd frontend && npx vitest run tests/components/Layout.test.tsx

# Run in watch mode during development
cd frontend && npx vitest tests/components/BetaRoute.test.tsx --watch
```

### Full Validation (both stacks)

```bash
# Backend
pytest tests/ --cov=src --cov-report=term-missing -q

# Frontend
cd frontend && npm test -- --run

# Lint
ruff check src/
```

---

## Summary

| Category | Test Count |
|----------|-----------|
| Backend Unit Tests (model, schema, migration) | 13 |
| Backend Unit Tests (seed-users CLI) | 9 |
| Backend Integration Tests (API) | 4 |
| Frontend Unit Tests (AuthContext) | 4 |
| Frontend Unit Tests (Layout) | 8 |
| Frontend Unit Tests (BetaRoute) | 7 |
| Frontend Unit Tests (i18n) | 5 |
| Frontend Integration Tests | 3 |
| Edge Cases | 13 |
| **Total new tests** | **~66** |
| Existing test files requiring mock updates | 6 |

### Test File Locations

**Backend (new tests in existing files):**
- `tests/auth/test_user_model.py` -- add `test_user_default_role_*`, `test_user_role_*`
- `tests/auth/test_auth_router.py` -- update `_mock_user_row()` defaults, add `test_get_me_returns_role_*`
- `tests/cli/test_seed_users.py` -- add `test_creates_guest_user`, `test_guest_*`

**Backend (new files):**
- `tests/database/test_role_migration.py` -- migration idempotency tests

**Frontend (new files):**
- `frontend/tests/components/BetaRoute.test.tsx` -- new route guard tests
- `frontend/tests/i18n/betaBlocked-keys.test.tsx` -- new i18n key tests (or extend `locales.test.ts`)
- `frontend/tests/contexts/AuthContext.test.tsx` -- `hasBetaAccess` tests (or extend existing)

**Frontend (modified files):**
- `frontend/tests/components/Layout.test.tsx` -- add `mockAuthGuest` fixture + guest beta tests
- `frontend/tests/components/AdminRoute.test.tsx` -- update mock to include `hasBetaAccess`
- `frontend/tests/components/ProtectedRoute.test.tsx` -- update mock to include `hasBetaAccess`
