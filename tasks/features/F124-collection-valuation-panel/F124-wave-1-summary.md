# F124 — Wave 1 summary

**Status:** completed
**Tasks:** F124-T04, F124-T06, F124-T09
**Generated:** 2026-09-13T00:00:00Z (approximate; work is uncommitted on `main`, no per-Wave commit markers found)

## Files touched
- `frontend/src/components/DashboardInvestmentSummary.tsx` (T04: new — investment KPIs + progress bar, empty/error/loading states, testids `dashboard-investment*`)
- `frontend/src/components/__tests__/DashboardInvestmentSummary.test.tsx` (T04: new)
- `src/collectors/liga_url_recorder.py` (T06: new — `record_liga_url(repo, external_id, page_url)`, swallows exceptions, logs warning)
- `src/collectors/liga_sweep.py`, `src/collectors/scan.py`, `src/api/routers/collection.py`, `src/api/routers/cards.py`, `src/cli/main.py` (T06: all 5 writers call `record_liga_url` after a successful observation insert)
- `tests/collectors/test_liga_url_recorder.py` (T06: new unit tests)
- `tests/collectors/test_liga_sweep.py`, `tests/api/test_collection_refresh_liga.py`, `tests/unit/api/test_cards_refresh_price.py`, `tests/cli/test_push_prices.py` (T06: extended for URL recording)
- `frontend/src/pages/MyCollection.tsx` (T09: `CollectionCardTile` mounts `PaidPriceQuickEdit` under `showPaidPrice`/`onPaidPriceSaved` props; `handlePaidPriceSaved` updates tile state + bumps `portfolioRefreshKey`; `<PortfolioDashboard refreshKey={portfolioRefreshKey} />`)
- `frontend/src/components/PortfolioDashboard.tsx` (T09: new optional `refreshKey` prop added to the summary/history fetch `useEffect` deps)
- `frontend/src/components/__tests__/PortfolioDashboard.test.tsx` (T09: extended for `refreshKey`)
- `frontend/src/pages/__tests__/MyCollectionPaidPrice.test.tsx` (T09: new)

## Decisions
- T06 centralized the upsert in one shared helper (`liga_url_recorder.py`) rather than duplicating try/except logic across 5 writers, per the task's implementation guidance.
- _none_ beyond what T04/T06/T09 task files already specified — no deviations noted.

## Notes for next Wave
- Wave 2 (T07, T08) can rely on: `record_liga_url` already wired into every Liga writer (T06), so `liga_card_urls` will be populated going forward — T07 only needs to *read* it.
- `DashboardInvestmentSummary` (T04) is built but **not yet mounted** in `Dashboard.tsx` — that is T08's job.
- `frontend/src/types/api.ts` `PortfolioSummary.unpriced_card_count` (added Wave 0 by T03) is consumed by T04; T07 will add `ligamagic_url` to `CardDetail` in the same file next — sequential edit per the conflict map, no collision expected.
- None of this Wave's work is committed yet; git status still shows Wave 0 + Wave 1 changes together as modified/untracked on `main` — confirm commit strategy before Wave 2 starts.

DIDIO_DONE: techlead wrote F124-wave-1-summary.md
