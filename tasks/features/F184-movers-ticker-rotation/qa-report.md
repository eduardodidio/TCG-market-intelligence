# QA Report -- F184 + F185

**QA Agent** | **Date:** 2026-09-29

---

## F184 -- Auto-rotating Movers Ticker on Dashboard

**Verdict: PASS**

### Acceptance Criteria Verification

| # | Criterion | Result |
|---|-----------|--------|
| 1 | Dashboard shows horizontal ticker bar above KPI cards | PASS -- MoversTicker rendered in Dashboard.tsx, DOM ordering verified by `compareDocumentPosition` test |
| 2 | Ticker scrolls continuously left with card name + change % with color | PASS -- `animate-ticker` CSS class, green (`text-emerald-400`) for gainers, red (`text-red-400`) for losers, sign + arrow + percentage |
| 3 | Ticker pauses on hover | PASS -- CSS `hover:animation-play-state: paused` via `animate-ticker` class (verified in test) |
| 4 | Ticker hidden when movers data is empty or loading | PASS -- returns `null` on loading or empty items (2 dedicated tests) |
| 5 | Existing CollectionMovers grid remains below, unchanged | PASS -- Dashboard integration test confirms both components coexist |
| 6 | Works on mobile (no layout break) | PASS -- `w-full`, `overflow-hidden`, no fixed widths |
| 7 | Supports dark mode | PASS -- uses `bg-slate-800/80`, `border-slate-700`, `text-slate-200` which are inherently dark-mode compatible |
| 8 | `motion-reduce:` respects prefers-reduced-motion | PASS -- `motion-reduce:animate-none motion-reduce:overflow-x-auto` classes present, verified by test |

### Tests Run

- **Frontend:** 18 tests passed (10 MoversTicker + 8 Dashboard), 0 failed
- All tests in `src/components/__tests__/MoversTicker.test.tsx` and `src/pages/__tests__/Dashboard.test.tsx`

### TechLead Issues Addressed

1. **Duplicated items keyboard-focusable (minor):** FIXED. Added `tabIndex` prop to `MoversTickerItem` interface and component, and passed `tabIndex={index >= items.length ? -1 : undefined}` in the `MoversTicker.tsx` map call, matching the `MarketTicker.tsx` pattern (line 39). New test added to verify duplicated items have `tabindex="-1"` while originals do not.

2. **Duration formula comment (minor, informational):** Not addressed -- this is a non-blocking observation about code clarity. The formula works correctly.

### Test Gaps Filled

- Added 1 new test: `"sets tabIndex=-1 on duplicated items to prevent double keyboard focus"` -- verifies that the first half of items (originals) are keyboard-focusable while the second half (duplicates for seamless loop) are excluded from tab order.

### Files Modified (QA fixes)

- `frontend/src/components/MoversTickerItem.tsx` -- added `tabIndex` prop to interface and button element
- `frontend/src/components/MoversTicker.tsx` -- added `tabIndex={index >= items.length ? -1 : undefined}` to map call
- `frontend/src/components/__tests__/MoversTicker.test.tsx` -- added tabIndex accessibility test

---

## F185 -- Movers Percentage Integrity Fix

**Verdict: PASS**

### Acceptance Criteria Verification

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `get_movers()` applies R$0.50 minimum price floor | PASS -- `earliest.c.price_start >= 0.5` at line 1076 of repository.py |
| 2 | `get_movers()` caps `change_pct` at +/-1000% | PASS -- `abs(m[6]) <= 1000.0` post-query filter at line 1083 |
| 3 | Market volatile endpoint applies same sanity filters | PASS -- volatile fallback uses `repo.get_movers()` which now includes filters |
| 4 | Price observation insertion rejects prices <= 0 | PASS -- `median_price <= 0` guard at line 405, allows None through |
| 5 | CLI `diagnose-prices` lists outlier observations (read-only) | PASS -- `@cli.command("diagnose-prices")` at line 3314, read-only verified by test |
| 6 | All existing tests continue to pass | PASS -- 41 backend tests passed |
| 7 | New tests cover the filter changes | PASS -- see breakdown below |

### Tests Run

- **Backend:** 41 tests passed, 0 failed
  - `test_market_movers_filters.py` -- 9 tests (price floor boundaries, percentage cap, combined filters)
  - `test_market_endpoints_filters.py` -- 12 tests (endpoint integration, service layer delegation)
  - `test_price_validation.py` -- 8 tests (zero, negative, None, mixed batches, structlog warning)
  - `test_cli_diagnose.py` -- 6 tests (penny prices, extreme ratios, clean data, limit option, read-only assertion)
  - Additional tests from existing suite -- 6 tests

### TechLead Issues

No blocking issues were found by the TechLead. All three minor observations are informational and non-blocking:
1. Float literal vs Decimal for price floor -- works correctly, stylistic only
2. Python-level percentage cap vs SQL HAVING -- optimization opportunity, not a bug
3. Division-by-zero guard -- defensive coding, good practice

### Test Gaps

No significant test gaps identified. The boundary-value testing (0.49 vs 0.50, 1000% vs 1001%) is thorough and covers the critical edge cases. The read-only assertion for `diagnose-prices` CLI is a strong safeguard.

### Diagrams

Both features have valid Mermaid diagrams:
- `docs/diagrams/F184-architecture.mmd` + `docs/diagrams/F184-journey.mmd`
- `docs/diagrams/F185-architecture.mmd` + `docs/diagrams/F185-journey.mmd`

---

## Summary

| Feature | Verdict | Frontend Tests | Backend Tests | Issues Fixed |
|---------|---------|---------------|---------------|--------------|
| F184    | PASS    | 18 passed     | --            | 1 (tabIndex a11y) |
| F185    | PASS    | --            | 41 passed     | 0 (none blocking) |

**Total tests: 59 passed, 0 failed.**

### Remaining Risks

- **Low:** The duration formula comment (F184 TechLead issue #2) is a readability nit, not a functional risk.
- **Low:** The Decimal vs float stylistic inconsistency (F185) has no functional impact since SQLAlchemy coerces correctly for both dialects.
- No P0 or P1 risks identified for either feature.
