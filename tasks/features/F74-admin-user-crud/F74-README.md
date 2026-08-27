# F74 — Admin User CRUD (Create/Delete + First-Access Password)

**Status:** done
**Wave structure:** Wave 1 (after F72, F73, F76)
**Dependencies:** None (but F75 depends on this)

## Summary

Add user creation and deletion to the admin panel. Admin creates users with a temporary first-access password that must be changed on first login. Soft-delete users (is_active=0).

## Tasks

| Task | Description | Wave |
|------|-------------|------|
| F74-T01 | Backend: DB schema + password expiration + admin endpoints | 1 |
| F74-T02 | Backend: Login flow password expiration check + force-change endpoint | 1 |
| F74-T03 | Frontend: Create user form + delete button + password change flow | 1 |
| F74-T04 | Full-stack tests | 1 |

## Acceptance Criteria

- Admin can create a user (email + display_name), gets temporary password in response
- Temporary password expires immediately (must be changed on first login)
- Login with expired password returns special response (password_expired flag)
- Frontend shows "change password" form when password_expired
- Admin can soft-delete users (sets is_active=0), cannot delete self
- Soft-deleted users cannot login
- Frontend shows create user form + delete button in admin Users section
