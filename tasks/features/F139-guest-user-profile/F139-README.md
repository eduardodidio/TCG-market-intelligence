# F139 — Guest User Profile

**Status:** planned
**Created:** 2026-09-18
**Priority:** P1

## Summary

Create a guest user (`guest@tedhmarket.com.br` / `mudar@12345`) that has the
same functional access as a regular authenticated user but **cannot interact
with Beta Test features**. Beta items remain visible in the sidebar (greyed
out / disabled) and attempting to click them displays the message:

> "Esta funcao nao esta habilitada para o perfil atual"

## Scope

| In scope | Out of scope |
|----------|--------------|
| `role` column on UserRow (`admin` / `guest`) | New role-based permission matrix beyond beta |
| `role` field exposed in UserProfile schema + JWT payload | Admin panel access for guest |
| Guest user seed in CLI `seed-users` | OAuth guest login |
| Frontend: disabled beta nav items for guest | Shared collection data between users |
| Frontend: BetaRoute guard (URL protection) | |
| Frontend: toast message on blocked interaction | |
| i18n for the blocked message (pt-BR + en) | |

## Architecture

### Backend

- **UserRow**: add `role: str` column (default `"admin"` for backward compat).
  Values: `"admin"`, `"guest"`.
- **UserProfile schema**: add `role: str` field.
- **`/auth/me`**: already returns full UserProfile — `role` auto-included.
- **`seed-users` CLI**: add guest user entry with `is_admin=0`, `role="guest"`,
  initial credits 10,000.

### Frontend

- **UserProfile type**: add `role: string` field.
- **AuthContext**: add computed `hasBetaAccess: boolean` (true when
  `role !== "guest"`).
- **Layout.tsx**: beta nav items render as disabled `<span>` (not `<Link>`)
  with `opacity-50 cursor-not-allowed` + `onClick` → toast.
- **BetaRoute component**: new guard wrapping beta routes in App.tsx.
  If `!hasBetaAccess`, renders a centered message card instead of `<Navigate>`.
- **i18n**: add `"betaBlocked"` key in both locales.

## Tasks

| ID | Title | Wave | Depends on |
|----|-------|------|------------|
| T01 | Backend: `role` column + schema + API | 0 | — |
| T02 | Backend: seed guest user in CLI | 1 | T01 |
| T03 | Frontend: beta access control (types, Layout, BetaRoute, toast, i18n) | 1 | T01 |

## Waves

- **Wave 0**: T01 (backend model change — prerequisite for everything)
- **Wave 1**: T02 + T03 (parallel — backend seed + frontend guards)

## Risks

- Alembic / migration: project uses raw SQLAlchemy without Alembic. Column
  addition done via `ALTER TABLE` in repo or manual migration.
- Existing users have no `role` — default `"admin"` preserves current behavior.
- Guest user needs credits to use card refresh features (same credit system).
