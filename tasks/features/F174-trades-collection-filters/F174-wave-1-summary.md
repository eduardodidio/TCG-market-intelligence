# F174 — Wave 1 summary

**Status:** completed
**Tasks:** F174-T03, F174-T04, F174-T05, F174-T06
**Generated:** 2026-09-24T19:00:00Z

## Files touched
- `src/marketplace/trade_queries.py` (T03: new `TradeQueries` — filtered/sorted listings, listing sets, duplicates, duplicate sets; does not touch `repository.py`)
- `tests/marketplace/test_trade_queries.py` (T03: 31 tests, all passing)
- `frontend/src/utils/cardListFilter.ts` (T04: pure `filterCardList`/`sortCardList`/`buildSetOptions`)
- `frontend/src/utils/tradeSortOptions.ts` (T04: trade sort option definitions)
- `frontend/src/utils/__tests__/cardListFilter.test.ts` (T04: 30 tests passing)
- `frontend/src/components/CardFilterBar.tsx` (T05: extracted sticky filter bar — search, set icons, sort, grid-size toggle, chips)
- `frontend/src/hooks/useCardListFilters.ts` (T05: URL-synced filter state hook)
- `frontend/src/components/__tests__/CardFilterBar.test.tsx`, `frontend/src/hooks/__tests__/useCardListFilters.test.tsx` (T05: 10 + 8 tests passing)
- `frontend/src/components/TradeCard.tsx` (T06: rewritten as collection-style grid tile, `aspect-[5/7]`, status badge, optional `compact` prop; existing testids/callbacks preserved)
- `frontend/src/components/__tests__/TradeCard.test.tsx` (T06: 11 tests passing)

## Decisions
- T03 followed the design decision from the README: new query module reuses `repo.engine`/`repo.get_latest_prices_batch`, `repository.py` untouched — zero risk of conflict with the parallel F171–F179 batch.
- _none_ beyond that (no scope changes observed in Wave 1 diffs).

## Notes for next Wave
- Task status fields in the task files are stale/inconsistent (only T04 is marked `Status: done`; T03/T05/T06 still say `planned` despite implementation + passing tests present) — Wave 2 owners (T07–T12) should verify actual code state via files/tests, not the `Status:` header, and update headers when picking up dependent work.
- All Wave 1 artifacts are present as **uncommitted** working-tree changes (new/untracked files, modified `TradeCard.tsx`) — nothing from this wave has been committed yet; Wave 2 developers should commit Wave 1 work (or confirm it's already staged) before building on `CardFilterBar`/`useCardListFilters`/`trade_queries.py` to avoid losing it.
- `CardFilterBar.tsx` is only 67 lines — confirm with T09/T10/T11/T12 that this is a complete extraction (search + set icons + sort + grid toggle + chips) and not a partial stub before wiring pages to it.
