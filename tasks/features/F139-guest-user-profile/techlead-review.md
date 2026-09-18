# F139 -- Guest User Profile: Tech Lead Review

**Reviewer:** Tech Lead Agent
**Date:** 2026-09-18
**Feature:** F139 -- Guest User Profile
**Branch:** homol

---

## Verdict: APPROVED_WITH_NOTES

The implementation is solid, well-structured, and follows project conventions.
The role system is cleanly designed with good backward compatibility. Tests are
thorough and cover the key scenarios. There are no blocking issues, but several
items deserve attention before or shortly after merging.

---

## Findings

### CRITICAL

None.

### MAJOR

#### M1. No backend enforcement of beta restrictions (frontend-only guard)

**Files:** `src/api/routers/` (all beta-related routers), `src/auth/dependencies.py`

The entire beta access control is enforced exclusively on the frontend via
`BetaRoute` and disabled sidebar items. There is **no backend middleware or
dependency** that prevents a guest user from calling beta-related API endpoints
directly (e.g., `POST /api/v1/decks/generate`, `GET /api/v1/market/trending`,
`GET /api/v1/achievements`).

A guest user with basic HTTP knowledge (or even browser DevTools) can bypass the
frontend guard and interact with all beta endpoints. While the PRD scoped this
as "out of scope" (no permission matrix beyond beta), this is a **known
security gap** that should be tracked as a follow-up.

**Recommendation:** Create a backlog item for a `require_beta_access` FastAPI
dependency that checks `user.role != "guest"` and returns 403 on beta endpoints.
This is not a blocker for F139 since the guest account is a demo profile with
limited real-world attack surface, but it should be documented.

#### M2. Missing ADR and diagrams

**Files:** `docs/adr/`, `docs/diagrams/`

Per CLAUDE.md documentation rules, every feature MUST:
1. Create an ADR under `docs/adr/` for significant architecture decisions.
2. Produce at least two Mermaid diagrams under `docs/diagrams/` (architecture +
   user journey).

F139 introduces a role system to the user model -- this is an architecture
decision that warrants an ADR (e.g., "Role column with frontend-only beta
gating"). No diagrams were produced either.

**Recommendation:** Add `docs/adr/XXXX-guest-role-frontend-beta-gating.md` and
`docs/diagrams/F139-architecture.mmd` + `docs/diagrams/F139-journey.mmd`.

#### M3. README.md not updated

Per CLAUDE.md: "every feature that ships MUST update the project README.md with
a short note of what was delivered." F139 adds a guest user role and beta access
control -- this should be mentioned.

### MINOR

#### m1. `decks/:id` route not wrapped in BetaRoute

**File:** `frontend/src/App.tsx:374-382`

The `/decks/:id` (DeckView) route is **not** wrapped in `BetaRoute`, while
`/decks`, `/decks/ranking`, and `/decks/build` are. This means a guest user who
knows a deck ID can navigate directly to `/decks/42` and view a deck page. This
may be intentional (view-only access to shared decks), but it is inconsistent
with the other deck routes being blocked.

Similarly, `/decks/evaluate` at line 370 is a redirect to `/decks?evaluate=true`
which itself is wrapped -- so that one is fine.

**Recommendation:** Clarify whether this is intentional. If not, wrap
`/decks/:id` in `<BetaRoute>` as well.

#### m2. `_mock_user_row` missing `password_expires_at`

**File:** `tests/auth/test_user_role.py:22-40`

The `_mock_user_row()` helper does not include `password_expires_at` in its
defaults dict. The `get_current_user` dependency at
`src/auth/dependencies.py:68` reads this attribute via `getattr(..., None)`, so
it works today. However, for completeness and to prevent future breakage if the
code changes to direct attribute access, it should be included.

```python
# Missing from defaults:
"password_expires_at": None,
```

#### m3. BetaRoute uses emoji (lock icon) via HTML entity

**File:** `frontend/src/components/BetaRoute.tsx:29`

```tsx
<div className="text-4xl mb-4" aria-hidden="true">&#x1F512;</div>
```

This renders a lock emoji in the blocked message card. The CLAUDE.md guidelines
say "avoid using emojis." This is a minor cosmetic choice in user-facing UI
(not documentation), so it is not a hard violation, but replacing it with an SVG
icon would be more consistent with the rest of the UI which uses SVG icons
throughout (see Layout.tsx `ICONS` object).

#### m4. Toast auto-dismiss timeout is 3 seconds

**File:** `frontend/src/components/Layout.tsx:129`

The beta-blocked toast auto-dismisses after 3 seconds. The existing UndoToast
pattern uses 5 seconds. For consistency, consider matching the 5-second delay.
This is purely cosmetic.

### NOTES

#### N1. `hasBetaAccess` is true when user is null (unauthenticated)

**File:** `frontend/src/contexts/AuthContext.tsx:198`

```typescript
const hasBetaAccess = !user || user.role !== "guest";
```

When `user` is `null` (unauthenticated), `hasBetaAccess` evaluates to `true`.
This is the correct behavior: anonymous users should not be blocked from public
beta routes (market, banlist). The `BetaRoute` component separately handles
the auth check via `requiresAuth`. This is well-designed.

#### N2. Role system is intentionally simple and extensible

The role column uses `String(20)` with values `"admin"` and `"guest"`. The
default is `"admin"` for backward compatibility. This is a good choice --
it keeps the migration trivial (additive `ALTER TABLE`) and avoids breaking
existing users. Future roles (e.g., `"beta_tester"`, `"viewer"`) can be added
without schema changes.

#### N3. Seed-users properly handles role drift correction

**File:** `src/cli/main.py:808-818`

If a guest user's role is manually changed (e.g., via DB admin), `seed-users`
detects the drift and corrects it. This is tested in
`tests/cli/test_seed_users.py:202-220`. Good defensive design.

#### N4. Guest password is hardcoded in the SEED_USERS dict

**File:** `src/cli/main.py:796`

The guest password `"mudar@12345"` is hardcoded in the source, not read from
an environment variable. This is intentional per the PRD (the guest account is
a public demo login). The admin password correctly uses `TCG_SEED_PASSWORD`.
This asymmetry is well-tested in `test_guest_password_is_hardcoded` and
`test_admin_password_uses_env_var`.

#### N5. Collection reassignment only targets admin (first seed user)

**File:** `src/cli/main.py:847-848`

```python
primary = repo.get_user_by_email(SEED_USERS[0]["email"])
```

The code uses `SEED_USERS[0]` (the admin) as the reassignment target, so guest
user never inherits orphaned collection entries. This is correct and tested.

#### N6. Test coverage is comprehensive

The implementation includes:
- **Backend:** 17 tests across `test_user_role.py` and `test_seed_users.py`
  covering model, schema, API response, migration idempotency, seed logic,
  password handling, credit grants, role drift correction, and collection
  reassignment.
- **Frontend:** 7 tests in `BetaRoute.test.tsx` and 4 guest-specific tests in
  `Layout.test.tsx` covering admin access, guest blocking, toast behavior,
  disabled styling, and public route access.
- Both locale files have the `beta.blocked` key with correct content.
- Existing test mocks (`mockAuthAuthenticated`, `mockAuthAdmin`,
  `mockAuthUnauthenticated`) are updated with `hasBetaAccess` and `role`.

---

## Architecture Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| Backward compatibility | Good | Default `role="admin"`, `getattr` fallbacks throughout |
| Migration safety | Good | Idempotent `ALTER TABLE` with column-existence check |
| Frontend guard design | Good | `BetaRoute` with `requiresAuth` prop is flexible |
| Backend enforcement | Gap | No API-level restriction for guest users (M1) |
| Test coverage | Good | 21+ new tests, existing mocks updated |
| i18n | Complete | Both locales have `beta.blocked` key |
| Documentation | Missing | No ADR, no diagrams, no README update (M2, M3) |

---

## Summary

F139 delivers a clean, minimal role system with proper backward compatibility
and good test coverage. The frontend beta access control is well-implemented
with both navigation-level (disabled sidebar items + toast) and route-level
(`BetaRoute` guard) protection.

The main gaps are: (1) the lack of backend enforcement, which should be tracked
as a follow-up; (2) missing ADR and diagrams per project conventions; and (3)
the README update requirement. The `/decks/:id` route gap (m1) should be
clarified as intentional or fixed.

None of these are blocking -- the feature is safe to ship as-is.
