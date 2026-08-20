# F14 — Collection UX Hotfixes: QA Report

**Verdict: PASS**

**Date:** 2026-08-20
**Tester:** QA Agent (Claude Opus 4.6)

---

## 1. Test Results

| Suite | Before QA | After QA | Status |
|-------|-----------|----------|--------|
| Backend (pytest) | 715 passed | 715 passed | GREEN |
| Frontend (vitest) | 205 passed | 212 passed | GREEN |
| Backend coverage | 91.80% | 91.80% | Above 70% threshold |

## 2. Acceptance Criteria Verification

### F14-T01: Collection cards internal navigation + external links

| AC | Status | Notes |
|----|--------|-------|
| Clicking collection card with `card_id` navigates to `/cards/{card_id}` | PASS | `CollectionCardTile` wraps in `<Link to={/cards/${card.card_id}}>`. Test: `linked card (with card_id) navigates to /cards/{card_id}` |
| Clicking collection card WITHOUT `card_id` stays internal | PASS | Navigates to `/cards?name={name}&set={set}` via internal `<Link>`. Test: `unlinked card (no card_id) navigates to internal Explore page with filters` |
| CardDetail shows Scryfall external link | PASS | Correct URL with `set:` suffix when set_code exists, without when null. Tests: `renders Scryfall external link with correct URL`, `renders Scryfall link without set code when set_code is null` |
| CardDetail shows LigaMagic external link | PASS | Correct URL format. Test: `renders LigaMagic external link with correct URL` |
| External links open in new tab | PASS | Both links have `target="_blank"` and `rel="noopener noreferrer"`. Verified in tests |
| All existing tests pass + new tests cover link rendering | PASS | 6 tests cover link rendering |

### F14-T02: Fix per-card price display

| AC | Status | Notes |
|----|--------|-------|
| Collection card tile displays price in BRL | PASS | `formatBRL(card.latest_price)` with `data-testid="card-price"`. Test: `displays formatted price for card with latest_price` |
| Cards without price show clear indicator | PASS | `formatBRL(null)` returns `"--"`, styled with `text-slate-500`. Test: `displays '--' fallback for card with null latest_price` |
| Collection summary "Est. Value" reflects sum | PASS | Uses `formatBRL(summary.total_value)` with `"--"` fallback. **New tests** added for both cases |
| Backend schema uses `float` not `Decimal` | PASS | `latest_price: float | None = None` in `collection.py` and `cards.py` schemas |
| `formatBRL` handles edge cases defensively | PASS | Handles null, undefined, NaN, string coercion, non-numeric strings. **New tests** added for very large numbers and NaN |

### F14-T03: Infinite scroll (Collection + Explore Cards)

| AC | Status | Notes |
|----|--------|-------|
| Collection page auto-loads on scroll | PASS | `useInfiniteScroll` hook with sentinel div. `enabled: !!cursor && !loadingMore` |
| Explore Cards page auto-loads on scroll | PASS | Same pattern as Collection page |
| Loading indicator shown while fetching | PASS | `data-testid="loading-more"` spinner renders when `loadingMore` is true |
| No duplicate cards | PASS | Cursor-based pagination + guard `if (!cursor \|\| loadingMore) return` |
| "Load More" button removed | PASS | `Pagination.tsx` fully deleted. No references remain in source code |
| `useInfiniteScroll` hook tested | PASS | 9 tests: ref creation, observer lifecycle, intersection callback, rootMargin, cleanup |

## 3. Regression Checks

| Check | Status | Notes |
|-------|--------|-------|
| No broken imports to deleted Pagination | PASS | `grep -r "Pagination" frontend/src/` returns zero results |
| CardTile.tsx (Explore) not modified by T01 | PASS | File unchanged -- uses same `<Link>` pattern, unmodified |
| Backend endpoints return correct shapes | PASS | `latest_price: float \| None` in schemas; `median_price` from `get_latest_prices_batch()` fed through |
| No dangling "Load more" text in source | PASS | Only a code comment `// Load more handler` remains in `Cards.tsx` (harmless) |

## 4. Tests Added by QA (7 new tests)

### `tests/utils/format.test.ts` (+2)
- `formatBRL` > formats very large numbers with thousand separators
- `formatBRL` > returns '--' for NaN

### `tests/pages/MyCollection.test.tsx` (+4)
- MyCollection -- infinite scroll > renders scroll sentinel when cards are loaded
- MyCollection -- infinite scroll > does not render a load-more button (replaced by infinite scroll)
- MyCollection -- summary KPI > displays Est. Value with formatted BRL when total_value exists
- MyCollection -- summary KPI > displays '--' for Est. Value when total_value is null

### `tests/pages/CardDetail.test.tsx` (+1)
- CardDetail page > renders '--' for latest price when latest_price is null

## 5. Remaining Risks

- **Scroll position on back-navigation**: The AC mentions "scroll position preserved when navigating back from a detail view." This relies on browser native behavior with React Router; it is not explicitly tested (would require e2e/integration testing with a real browser). Low risk since there is no explicit `scrollTo(0,0)` on mount.
- **Mobile viewport**: Infinite scroll on touch devices is not unit-testable. Recommend manual verification on a mobile viewport. Low risk since `IntersectionObserver` is well-supported across mobile browsers.
- **Data availability**: If `snapshot-prices` has not been run, all prices will be null. The UI handles this gracefully with `"--"` fallback. Not a code issue.

## 6. Summary

All three tasks meet their acceptance criteria. No production bugs found. Seven additional tests were written to fill coverage gaps in price formatting edge cases, collection scroll sentinel rendering, and summary KPI display. Total frontend tests: 212, all passing. Backend: 715 tests, all passing, 91.80% coverage.
