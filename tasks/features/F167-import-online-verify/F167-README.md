# F167 — Import Cards Online Verification

**Status:** planned
**Wave:** 0 (parallel with F164, F165, F166)
**Tasks:** 2
**Files touched:** new test files only (+ possible BetaRoute migration if issues found)

## Summary

User suspects the import purchases feature only works locally. Investigation shows the code uses standard web APIs (FormData, UploadFile) with no local-only dependencies. This feature adds integration tests to prove it works online, and if issues are found, moves the feature behind BetaRoute.

## Analysis

After reviewing `src/api/routers/purchases.py` and `frontend/src/api/purchases.ts`:
- Backend uses `UploadFile` (FastAPI standard) — works on any deployment
- Frontend uses `FormData` + `fetch` with `API_BASE_URL` — works with any backend URL
- No file system access, no local paths, no SQLite-specific code
- `purchase_parser.py` and `purchase_matcher.py` are pure Python, no local dependencies
- **Conclusion: Should work online.** Tests will confirm.

## Tasks

| Task | Description | Wave |
|------|-------------|------|
| F167-T01 | Integration tests for import endpoints | 0 |
| F167-T02 | Conditional: move to BetaRoute if issues found | 0 |

## Architecture Notes

- If tests pass: feature stays in PRIMARY_NAV_ITEMS (current state)
- If tests reveal issues: wrap route in BetaRoute, add to BETA_NAV_ITEMS
- Test should use actual endpoint with test DB, not mocks
