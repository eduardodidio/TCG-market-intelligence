# F22 -- Authentication (Login Area)

**Status:** planned
**Priority:** high (blocks F19 user preferences, F23 deck import)

## Problem Statement

The application currently has no authentication. All data (collection,
scans, analytics) is accessed via a hardcoded `FAKE_USER_ID = "eduardo"`
in the collection router. There is no concept of user accounts, no
login flow, and no route protection.

This means:
- Anyone with the URL can view and modify the collection.
- There is no way to support multiple users.
- Features like user preferences (F19) and deck import (F23) cannot
  scope data per user.

## Goals

1. Users can sign in via Google, Microsoft, Apple, or email+password.
2. Unauthenticated users can browse public areas (Explore Cards, public
   prices, search, Dashboard, Market Movers).
3. Authenticated users gain access to protected areas (My Collection,
   collection card detail, Price Scans, future: preferences, deck import).
4. Unauthenticated users attempting to access protected areas are
   redirected to the login page.
5. Existing collection data is migrated from `FAKE_USER_ID` to the
   first authenticated user.

## Non-Goals

- Role-based access control (admin vs user) -- defer to a future feature.
- Multi-factor authentication -- defer.
- Email verification flow -- defer (OAuth users are pre-verified; email
  users will be trusted on first registration for now).
- Password reset flow -- defer (can be added incrementally).
- Rate limiting on auth endpoints -- defer (the API already has a basic
  API key guard for write operations).

## Technical Approach

### Backend

- **User table** (`users`): stores user identity, auth provider, hashed
  password (for email auth), profile metadata.
- **Auth library**: `authlib` for OAuth2 client (Google, Microsoft, Apple).
  `passlib[bcrypt]` for email+password hashing.
- **JWT tokens**: `python-jose[cryptography]` for issuing and validating
  JWT access tokens (short-lived) and refresh tokens (longer-lived).
  Tokens stored in httpOnly cookies (for frontend) and also accepted
  via `Authorization: Bearer` header (for API clients).
- **FastAPI dependency**: `get_current_user()` dependency that extracts
  and validates the JWT, returning a `User` domain object. Optional
  variant `get_optional_user()` for endpoints that work both ways.
- **Auth router**: `/api/v1/auth/*` endpoints for login, register,
  OAuth callbacks, token refresh, logout.
- **Collection migration**: one-time migration of existing
  `user_collection` rows from `user_id="eduardo"` to the first
  authenticated user's ID.

### Frontend

- **AuthContext**: React context providing `user`, `isAuthenticated`,
  `login()`, `logout()`, `isLoading`.
- **Login page**: `/login` with OAuth buttons and email+password form.
- **ProtectedRoute wrapper**: wraps routes that require auth; redirects
  to `/login` with `returnTo` query param.
- **API client changes**: attach JWT token (from cookie or localStorage)
  to requests. Handle 401 responses by redirecting to login.
- **Layout changes**: replace `FAKE_USER` with real user data; show
  login/logout button; conditionally show nav items.

### Access Control Matrix

| Area              | Route            | Auth Required |
|-------------------|------------------|---------------|
| Dashboard         | `/`              | No            |
| Explore Cards     | `/cards`         | No            |
| Card Detail       | `/cards/:id`     | No            |
| Market Movers     | `/market/movers` | No            |
| My Collection     | `/collection`    | Yes           |
| Collection Detail | `/collection/:id`| Yes           |
| Price Scans       | `/scans`         | Yes           |
| Login             | `/login`         | No            |

### Security Considerations

- Passwords hashed with bcrypt (cost factor 12).
- JWT secret from environment variable `TCG_JWT_SECRET` (required in
  production; auto-generated in dev mode).
- Access tokens expire in 30 minutes; refresh tokens in 7 days.
- OAuth state parameter validated to prevent CSRF.
- CORS policy may need tightening for production (currently `*`).
- httpOnly cookies for token storage prevent XSS token theft.

## Dependencies

- New Python packages: `authlib`, `passlib[bcrypt]`, `python-jose[cryptography]`
- Frontend: no new packages (native fetch + React context)
- Environment variables: `TCG_JWT_SECRET`, `TCG_GOOGLE_CLIENT_ID`,
  `TCG_GOOGLE_CLIENT_SECRET`, `TCG_MICROSOFT_CLIENT_ID`,
  `TCG_MICROSOFT_CLIENT_SECRET`, `TCG_APPLE_CLIENT_ID`,
  `TCG_APPLE_CLIENT_SECRET`

## Success Metrics

- Users can register and log in via all 4 methods.
- Protected routes redirect to login when unauthenticated.
- Existing collection data is accessible after first login.
- All existing tests pass (857+ backend, 304+ frontend).
- New auth tests achieve >= 90% coverage on auth modules.
- No regression in page load or API response times.

## Out of Scope / Future Work

- F19: User preferences (depends on F22 user model).
- F23: Deck import (depends on F22 user scoping).
- Admin panel, user management.
- Password reset, email verification.
