# ADR-0013: Guest User Role System

## Status
Accepted

## Context
The platform needs a demo/guest login for visitors. Beta Test features should be visible but disabled for guest users.

## Decision
Added a `role` column (VARCHAR(20), default "admin") to the users table. Frontend checks `role !== "guest"` for beta access. Backend enforcement deferred to follow-up (frontend-only gating is acceptable for demo/preview restriction, not security-critical data).

## Consequences
- All existing users default to "admin" role (backward compatible)
- New roles can be added without schema changes (string-based, not enum)
- Beta restrictions are UI-level only -- API endpoints remain accessible to any authenticated user
