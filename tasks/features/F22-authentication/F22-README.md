# F22 -- Authentication (Login Area)

**Status:** planned

## Summary

Add user authentication with four providers (Google, Microsoft, Apple,
email+password). Introduce a `users` table, JWT-based sessions, FastAPI
auth dependencies, a React AuthContext, a login page, and protected route
guards. Existing collection data migrates from the hardcoded
`FAKE_USER_ID` to the first authenticated user.

## Architecture Impact

- `src/database/models.py` -- new `UserRow` table
- `src/domain/models.py` -- new `User`, `AuthProvider` domain models
- `src/auth/` -- **new package**: `passwords.py`, `jwt.py`, `oauth.py`, `dependencies.py`
- `src/api/routers/auth.py` -- **new file**: login, register, OAuth, refresh, logout
- `src/api/routers/collection.py` -- replace `FAKE_USER_ID` with `get_current_user`
- `src/api/routers/scans.py` -- add auth guard
- `src/api/app.py` -- register auth router
- `src/database/repository.py` -- user CRUD methods
- `frontend/src/contexts/AuthContext.tsx` -- **new file**
- `frontend/src/pages/Login.tsx` -- **new file**
- `frontend/src/components/ProtectedRoute.tsx` -- **new file**
- `frontend/src/components/Layout.tsx` -- replace FAKE_USER with real user
- `frontend/src/api/client.ts` -- attach auth token, handle 401
- `frontend/src/api/auth.ts` -- **new file**: auth API calls
- `frontend/src/App.tsx` -- wrap with AuthProvider, add login route, protect routes
- `pyproject.toml` -- new deps: `authlib`, `passlib[bcrypt]`, `python-jose[cryptography]`

## Wave Manifest

- **Wave 0**: F22-T01, F22-T02               (User DB model + domain models, auth utility modules)
- **Wave 1**: F22-T03                          (repository user CRUD, depends on T01)
- **Wave 2**: F22-T04, F22-T05                (FastAPI auth deps + auth router, parallel after T01-T03)
- **Wave 3**: F22-T06                          (protect backend endpoints, depends on T04)
- **Wave 4**: F22-T07, F22-T08                (frontend AuthContext + Login page, parallel)
- **Wave 5**: F22-T09                          (frontend route guards + Layout, depends on T07+T08)
- **Wave 6**: F22-T10                          (collection data migration + diagrams + docs)

## Global Acceptance Criteria

- [ ] Users can register with email+password
- [ ] Users can log in via Google, Microsoft, Apple OAuth2
- [ ] JWT tokens are issued and validated correctly
- [ ] Protected API endpoints return 401 when unauthenticated
- [ ] Protected frontend routes redirect to `/login`
- [ ] Public routes (Dashboard, Explore Cards, Market Movers) remain accessible
- [ ] Collection endpoints use the authenticated user's ID
- [ ] Existing collection data migrates to the first authenticated user
- [ ] All existing tests pass (857+ backend, 304+ frontend)
- [ ] New tests added for all layers (coverage >= 90% on auth modules)
- [ ] README.md updated with F22 delivery notes

## Diagrams

- `docs/diagrams/F22-architecture.mmd` -- auth flow, token lifecycle, component diagram
- `docs/diagrams/F22-journey.mmd` -- user journeys for login, registration, protected access
