# Tech Lead Review -- F14 Collection UX Hotfixes

**Reviewer:** Tech Lead agent
**Date:** 2026-08-20
**Verdict:** APPROVED

---

## Summary

All three tasks are well-executed. The code is clean, consistent with existing patterns, properly tested, and introduces no regressions. No blockers found.

---

## T01 -- Card Navigation + External Links

**Files reviewed:**
- `frontend/src/pages/MyCollection.tsx`
- `frontend/src/pages/CardDetail.tsx`
- `frontend/tests/pages/MyCollection.test.tsx`
- `frontend/tests/pages/CardDetail.test.tsx`

### Findings

**Architecture** -- Clean and correct. The `CollectionCardTile` click handler now uses React Router `<Link>` for both linked cards (`/cards/{card_id}`) and unlinked cards (`/cards?name=...&set=...`). No more `window.open` to Scryfall. External links (Scryfall, LigaMagic) are correctly placed in `CardDetail.tsx` where they belong.

**Security** -- All external `<a>` tags use `target="_blank" rel="noopener noreferrer"`. Card names in URLs use `encodeURIComponent`. No XSS vectors.

| # | Finding | Severity |
|---|---------|----------|
| 1 | The Scryfall search URL appends `+set:{set_code}` without encoding the set code. Set codes are short alphanumeric strings (e.g. "DMR", "MH2") so this is safe in practice, but strictly speaking it should also be encoded. | NOTE |
| 2 | The "Unknown Card" guard on line 149 of `MyCollection.tsx` correctly avoids sending the display-name fallback as a search filter. Good edge-case handling. | -- |

**Tests** -- 3 new navigation tests cover linked, unlinked, and no-name scenarios. 4 new external-links tests in CardDetail verify Scryfall and LigaMagic URLs (with and without set_code), `target="_blank"`, and `rel` attributes. Adequate coverage.

---

## T02 -- Price Display Fix (Decimal to float)

**Files reviewed:**
- `src/api/schemas/collection.py`
- `src/api/schemas/cards.py`
- `tests/api/test_schemas.py`
- `frontend/src/utils/format.ts`
- `frontend/src/pages/MyCollection.tsx`
- `frontend/tests/utils/format.test.ts`
- `frontend/tests/pages/MyCollection.test.tsx`

### Findings

**Root cause analysis** -- Correct. The database stores `median_price` as `Numeric(12,2)`, which SQLAlchemy maps to Python `Decimal`. Pydantic's default JSON serialization of `Decimal` produces a string (e.g., `"3.50"`), not a number. The fix changes `latest_price` to `float | None` in both `CardSummary`, `CardDetail`, and `CollectionCard` schemas. Pydantic now coerces `Decimal` -> `float` during validation, so the JSON output is a proper number.

**Frontend defense-in-depth** -- `formatBRL` now accepts `number | string | null | undefined` and handles string coercion with `parseFloat`. This is good defensive coding -- even if the backend fix is reverted, the frontend won't break.

**Price indicator** -- The conditional class `text-cyan-400` vs `text-slate-500` based on `latest_price != null` is clean and tested.

| # | Finding | Severity |
|---|---------|----------|
| 1 | `PriceObservation` schema still uses `Decimal` for `median_price`, `tcg_price`, `last_sold_price`. This is intentional -- those fields go through the price chart, which handles `Decimal` fine via Recharts numeric parsing. But if this causes issues later, the same pattern (Decimal -> float) should be applied. | NOTE |
| 2 | The `TestDecimalRoundTrip.test_card_summary_float_roundtrip` test on line 231 of `test_schemas.py` asserts `isinstance(restored.latest_price, float)` -- good, confirms the coercion. | -- |

**Tests** -- 2 new format tests (string coercion, non-numeric string). 2 new MyCollection tests (price display, null-price fallback). Backend round-trip test added. Coverage is solid.

---

## T03 -- Infinite Scroll

**Files reviewed:**
- `frontend/src/hooks/useInfiniteScroll.ts`
- `frontend/src/pages/MyCollection.tsx`
- `frontend/src/pages/Cards.tsx`
- `frontend/tests/hooks/useInfiniteScroll.test.ts`
- `frontend/tests/pages/Cards.test.tsx`
- `frontend/tests/setup.ts`

### Findings

**Architecture** -- The `useInfiniteScroll` hook is minimal and well-designed: takes a callback and `{ enabled, rootMargin? }`, returns a ref for the sentinel div. The `IntersectionObserver` is created only when `enabled` is true and the sentinel is mounted. Cleanup via `observer.disconnect()` on unmount or when `enabled` flips to false.

**Both pages** use the same pattern:
```
const sentinelRef = useInfiniteScroll(handleLoadMore, {
  enabled: !!cursor && !loadingMore,
});
```
This correctly prevents: (a) fetching when there's no next page, (b) double-fetching while a load is in progress.

**Pagination removal** -- `Pagination.tsx` and its test are deleted. No imports remain anywhere in `src/` or `tests/`. Only a stale coverage HTML artifact remains (harmless).

| # | Finding | Severity |
|---|---------|----------|
| 1 | The `useInfiniteScroll` hook does not debounce or throttle the `onLoadMore` callback. If the `IntersectionObserver` fires multiple times before the parent sets `loadingMore=true`, multiple fetches could be triggered. In practice the `enabled` flag and the guard `if (!cursor \|\| loadingMore) return` in `handleLoadMore` prevent this, but a more robust approach would be to track an internal `loading` ref in the hook itself. | WARNING |
| 2 | The `rootMargin: "200px"` default means the observer fires 200px before the sentinel enters the viewport. This is a good UX tradeoff for pre-fetching. | -- |
| 3 | The hook test file defines its own `MockIntersectionObserver` class, separate from the global one in `setup.ts`. This is fine -- the test needs to capture the callback and options, which the setup mock does not expose. | NOTE |
| 4 | `setup.ts` adds a global `IntersectionObserver` mock so all component tests that render sentinels don't crash in jsdom. Correct approach. | -- |

**Tests** -- 8 hook tests covering: ref creation, observer lifecycle (create, observe, disconnect), intersection callbacks (intersecting and non-intersecting), rootMargin (default and custom), and cleanup on unmount/disable. 3 new Cards page tests verify sentinel rendering and absence of old load-more button. Adequate.

---

## Cross-cutting Checks

| Check | Status |
|-------|--------|
| TypeScript types match backend schemas | OK -- `latest_price: number \| null` in TS matches `float \| None` in Pydantic |
| No `window.open` or external redirects from card clicks | OK -- all card clicks use `<Link>` for internal navigation |
| External links use `rel="noopener noreferrer"` | OK -- both Scryfall and LigaMagic links |
| No new dependencies introduced | OK |
| No hardcoded secrets or env values | OK |
| Backend tests: 715 passed, 91.80% coverage | OK |
| Frontend tests: 205 passed | OK (up from 192, net +13 new tests) |

---

## Final Verdict

**APPROVED** -- No blockers. One WARNING (potential double-fire of IntersectionObserver) is mitigated by existing guards in both `handleLoadMore` callbacks. All three tasks are production-ready.
