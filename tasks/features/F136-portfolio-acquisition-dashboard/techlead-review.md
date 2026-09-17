# F136 Tech Lead Review -- Portfolio Dashboard Revision

**Reviewer:** Tech Lead (automated)
**Date:** 2026-09-17
**Feature:** F136 -- Portfolio Dashboard Revision (Acquisition-Only View)
**Verdict:** APPROVED

---

## Summary

F136 implements investment-focused filtering and visualization for the
portfolio system across 5 tasks in 3 waves. The implementation is clean,
well-structured, and achieves all acceptance criteria from the PRD. Backend
filters use proper SQLAlchemy IS/IS NOT NULL predicates, the portfolio
summary endpoint now populates `cards_without_acquisition`, movers support
`investment_only` filtering, and the frontend adds a P&L sparkline, alert
banner, and collection filter chips with deep-link support.

---

## Checklist Review

### 1. Backend filter: `has_acquisition_price` (T01) -- PASS

- **Router** (`collection.py:112-114`): `has_acquisition_price: bool | None = Query(default=None)`
  correctly accepts tri-state (true/false/omitted).
- **Repository** (`repository.py:1588-1591`): `list_collection` applies
  `UserCollectionRow.acquisition_price.isnot(None)` for `True` and
  `.is_(None)` for `False`. Uses SQLAlchemy ORM predicates, not raw SQL.
- **Count consistency** (`repository.py:1661-1664`): `count_collection`
  mirrors the same filter logic, so pagination totals match filtered results.
- **Router passes filter to both** (`collection.py:130, 198`): Both
  `list_collection` and `count_collection` receive `has_acquisition_price`.
- **Backward compatibility**: `None` default means no filter applied when
  param is omitted. Confirmed by test `test_no_filter_returns_all`.

### 2. Portfolio summary: `cards_without_acquisition` (T02) -- PASS

- **New repo method** (`repository.py:4092-4102`):
  `count_entries_without_acquisition` counts entries where
  `acquisition_price IS NULL`. Clean, single-purpose query.
- **Schema** (`collection.py:172`): `cards_without_acquisition: int = 0`
  added to `PortfolioSummary` with safe default.
- **Router** (`collection.py:319, 329, 370`): Calls the new method and
  populates the field in both the zero-investment and normal code paths.
- **`unpriced_card_count`** (`collection.py:342-355`): The existing field is
  now properly populated by counting entries that have `acquisition_price`
  but lack a current market price observation.

### 3. Investment-only movers (T02) -- PASS

- **Router** (`collection.py:397-411`): `investment_only: bool = Query(default=False)`
  defaults to `False` for backward compatibility.
- **Filtering logic** (`collection.py:408-411`): When `investment_only=True`,
  fetches entries with acquisition via `get_collection_entries_with_acquisition`,
  builds a set of card IDs, and filters the trending dict. This is a clean
  in-memory filter that avoids a second DB query for trending data.
- **Potential concern**: For very large collections, fetching all entries with
  acquisition and then intersecting could be slow. However, this is bounded
  by the user's collection size (typically < 5000 cards), so acceptable.

### 4. Dashboard sparkline (T03) -- PASS

- **Component** (`DashboardInvestmentSummary.tsx:152-169`): Uses Recharts
  `ResponsiveContainer` + `LineChart` + `Line` with `type="monotone"`,
  `dot={false}`, and fixed 80px height. Clean sparkline implementation.
- **Data source**: Fetches `fetchPortfolioHistory(90)` for 90-day history,
  independent of the summary fetch. History error does not crash KPIs.
- **Guard** (`line 108`): `showSparkline` requires `!historyLoading && !historyError && history && history.length > 1`,
  preventing empty/single-point sparklines.
- **Loading state** (`line 171-176`): Shows skeleton placeholder while
  history loads.

### 5. Collection filter chips (T04) -- PASS

- **State initialization** (`MyCollection.tsx:308-315`): Reads
  `has_acquisition_price` from URL search params. Maps "true" to "with",
  "false" to "without", defaults to "all".
- **URL sync** (`MyCollection.tsx:582-584`): Syncs acquisition filter to URL
  params on change, enabling deep links.
- **API params** (`MyCollection.tsx:601-602`): `buildParams` includes the
  filter in API calls when active.
- **Clear filters** (`MyCollection.tsx:670-674`): `handleClearFilters` resets
  `acquisitionFilter` to "all".
- **Active filter detection** (`MyCollection.tsx:949`): `hasActiveFilters`
  includes `acquisitionFilter !== "all"` to show clear filters button.

### 6. Deep link from dashboard alert -- PASS

- **Alert link** (`DashboardInvestmentSummary.tsx:78, 211`):
  `to="/collection?has_acquisition_price=false"` -- correct URL that will be
  parsed by MyCollection's state initialization.
- **Alert visibility**: Shows in both the empty state (invested_card_count=0,
  line 76) and normal state (line 209). Only when
  `cards_without_acquisition > 0`.

### 7. Consistency: all movers use `investmentOnly=true` -- PASS

- **Dashboard.tsx:169**: `<CollectionMovers days={7} limit={3} investmentOnly />`
- **PortfolioDashboard.tsx:207**: `<CollectionMovers investmentOnly />`
- **API client** (`collection.ts:170-181`): `fetchCollectionMovers` correctly
  passes `investment_only=true` in query params only when `investmentOnly`
  is truthy. Does not send the param when false (prevents `investment_only=false`
  noise in URLs).

---

## Findings

### Positive

1. **Clean separation**: Backend filter logic lives in the repository layer,
   not duplicated in the router. Both `list_collection` and `count_collection`
   share the same filter pattern.
2. **Safe defaults**: `has_acquisition_price=None` and `investment_only=False`
   ensure backward compatibility with existing callers.
3. **Schema reuse**: The existing `unpriced_card_count` field in
   `PortfolioSummary` was reused rather than introducing a duplicate.
4. **Resilient sparkline**: History fetch failure is gracefully handled --
   KPIs still render, sparkline simply hides.
5. **Alert in both states**: The missing-acquisition alert shows even in the
   empty investment state (invested_card_count=0), which is the correct UX
   because users need to know they have cards without cost basis.
6. **URL deep-link round-trip**: Dashboard alert -> Collection filter ->
   URL param -> state initialization -> API call is a clean full cycle.

### Minor Observations (not blocking)

1. **`window.scrollTo` in tests**: The MyCollection tests emit
   `Error: Not implemented: window.scrollTo` warnings. This is a known jsdom
   limitation and does not affect test correctness, but a global mock in
   `vitest.setup.ts` would clean it up.
2. **Frontend `PortfolioSummary` type**: `unpriced_card_count` is typed as
   optional (`unpriced_card_count?: number`) while the backend schema has
   `unpriced_card_count: int = 0`. Not a bug (optional covers both present
   and missing), but could be `number` (non-optional) for consistency.
3. **Sparkline hardcoded to 90 days**: The `fetchPortfolioHistory(90)` call
   in the dashboard is not configurable. Fine for MVP but could be a prop.

---

## Recommendations

None blocking. The implementation meets all acceptance criteria and follows
existing patterns. Ship it.
