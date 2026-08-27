# F70 — Post-Review Hardening

**Status:** done
**Created:** 2026-08-27
**Priority:** P0 (security + data integrity)
**Depends on:** F69 (trading system)
**Origin:** TechLead full project review (`docs/reviews/full-review-20260827.md`)

## Summary

Address all BLOCKING findings from the TechLead review before shipping
further features. Focus areas: trade atomicity, auth security, frontend
error handling, and CI/build hygiene.

## Acceptance Criteria

1. Trade confirmation is race-condition-free (no double-spend)
2. `_complete_trade()` is atomic (all-or-nothing DB transaction)
3. MYP refresh deducts credits consistently (aligned with Liga)
4. Frontend API client handles 401 responses (auto-logout + redirect)
5. Dev mode auth bypass disabled when env vars missing
6. CORS restricted to specific HTTP methods
7. React Error Boundary catches render errors
8. `node_modules/` and frontend build artifacts in `.gitignore`
9. `package-lock.json` committed for reproducible builds
10. Dead "ambiguous" code removed from sync/match pipelines
11. All existing tests pass after changes
12. Marketplace router has integration tests for happy-path trade flow

## Waves

| Wave | Tasks | Description |
|------|-------|-------------|
| 0    | T01, T02, T03 | Backend security: trade atomicity, auth, CORS |
| 1    | T04, T05 | Frontend security: 401 handler, Error Boundary |
| 2    | T06, T07 | Build hygiene: .gitignore, lock files, dead code |
| 3    | T08 | Integration tests for marketplace trade flow |

## Non-goals

- No new features in this hardening pass
- No PRD/diagram backfill (separate task, not code)
- No provider test coverage increase (separate feature)
- No dependency version pinning (requires broader impact analysis)
