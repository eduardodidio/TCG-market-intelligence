# QA Report -- F07 Front-end Dashboard

**Agent:** QA
**Date:** 2026-08-18
**Feature:** F07 -- Front-end Dashboard

---

## 1. Test Execution

### Frontend Tests

- **Command:** `cd frontend && npm run test -- --run`
- **Result:** 165 passed, 0 failed (20 test files)
- **Duration:** ~5s

### Frontend Build

- **Command:** `cd frontend && npm run build`
- **Result:** Build succeeds in ~3s, zero warnings
- **Code splitting verified:** Recharts in CardDetail chunk (400KB), main bundle (238KB)

### Frontend Coverage

- **Command:** `npx vitest run --coverage` (v8 provider)
- **Overall:** 89.75% statements, 92.18% branches, 85.71% functions, 89.75% lines

| Area | Stmts | Notes |
|------|-------|-------|
| API client (client.ts) | 85% -> improved | Added 2 tests for `composeAbortSignals` |
| Components | 96.56% | All at 100% except PriceChart (82% -- chart internals not renderable in jsdom) |
| Hooks | 93.22% | useApi cleanup branch uncovered (acceptable) |
| Pages | 95.98% | Strong coverage across all 4 pages |
| Utils | 100% | format.ts and constants.ts fully covered |
| Entry points (App.tsx, main.tsx) | 0% | Expected -- entry points are not unit-testable |
| Types (api.ts) | 0% | Expected -- type-only file, no runtime code |

### Backend Tests

- **Command:** `cd /c/Workspace/TCG-market-intelligence && python -m pytest --tb=short -q`
- **Result:** 390 passed, 0 failed (50 warnings -- ResourceWarning, known)
- **Coverage:** 96.37% (above 70% threshold)
- **Verdict:** No regressions

---

## 2. TechLead Minor Notes -- Disposition

| TechLead Note | Action | Status |
|---------------|--------|--------|
| Unused `@/` path alias in tsconfig.json + vite.config.ts | Removed alias config and unused `path` import | FIXED |
| Unused `PERIOD_OPTIONS` in constants.ts | Removed dead export | FIXED |
| F07-README says "React Router v6" but actual is v7 | Corrected label to v7 | FIXED |
| `act()` warnings in PriceChart/Cards tests | Cosmetic console noise, tests pass correctly. Not fixing -- would require significant refactoring of async patterns for no functional benefit | NOTED |

---

## 3. Documentation Completeness

| Document | Path | Status |
|----------|------|--------|
| ADR-0003 | `docs/adr/0003-frontend-stack.md` | Present |
| PRD | `docs/prd/F07-frontend-dashboard.md` | Present |
| Architecture diagram | `docs/diagrams/F07-architecture.mmd` | Present |
| Journey diagram | `docs/diagrams/F07-journey.mmd` | Present |
| README.md (project) | `README.md` | Updated with F07 section |
| README.md (frontend) | `frontend/README.md` | Present |

---

## 4. Test Gaps Filled

### New tests added (2)

1. **`client.test.ts` -- "aborts when external signal fires (composeAbortSignals)"**
   Tests that passing an external `AbortSignal` to `apiGet` correctly composes it with the internal timeout signal, and aborting the external signal causes the request to abort.

2. **`client.test.ts` -- "handles already-aborted external signal"**
   Tests that passing an already-aborted signal to `apiGet` immediately aborts the request without hanging.

These tests cover the `composeAbortSignals` helper function (lines 84-97 of `client.ts`) which was previously at 0% coverage.

---

## 5. Remaining Notes

- **`act()` warnings:** PriceChart and Cards tests emit React 19 `act()` warnings in stderr. These are cosmetic -- all assertions pass correctly. Fixing would require wrapping async state updates in `act()` wrappers throughout the test files. This is a known React 19 testing pattern shift and is not blocking.

- **PriceChart internal coverage (82%):** The `formatChartDate` and `ChartTooltip` internal components (lines 31-71) are rendered inside Recharts `ResponsiveContainer`, which is mocked in jsdom (no layout engine). This is a known limitation of jsdom + Recharts testing and is acceptable.

- **`@vitest/coverage-v8` was not in devDependencies.** Installed it during QA to enable coverage reporting. This is a minor omission from Wave 0 scaffolding.

---

## 6. Verdict: PASSED

All 165 frontend tests pass. Build succeeds with code splitting working correctly. Backend 390 tests pass with no regressions. Coverage is strong at ~90% statements with known, justified gaps. Documentation is complete. TechLead minor notes addressed (3/4 fixed, 1 noted as cosmetic). Two new tests added to close the `composeAbortSignals` coverage gap.
