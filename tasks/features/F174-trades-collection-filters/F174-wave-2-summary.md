# F174 — Wave 2 summary

**Status:** completed
**Tasks:** F174-T07, F174-T08, F174-T09, F174-T10, F174-T11, F174-T12
**Generated:** 2026-09-24T19:25:00Z

## Files touched
- `src/api/routers/marketplace.py` (T07: `sort_by`/`sort_dir` params on `/marketplace/listings`, new `/marketplace/listings/sets` facet route)
- `src/marketplace/service.py` (T07: wires `TradeQueries` sort/filter into listing service)
- `tests/marketplace/test_router.py` (T07: new sort/facet cases)
- `src/api/routers/trade_match.py` (T08: filter/sort params on `/trade/duplicates`, new `/trade/duplicates/sets` facet route)
- `tests/api/test_trade_match_router.py` (T08: new filter/sort/facet cases)
- `frontend/src/pages/Marketplace.tsx`, `frontend/src/components/MarketplaceCardTile.tsx` (new), `frontend/src/api/marketplace.ts`, `frontend/src/pages/__tests__/Marketplace.test.tsx` (new) (T09: server-side search/set/sort, `CardFilterBar`, infinite scroll, tile grid)
- `frontend/src/pages/MyTrades.tsx`, `frontend/src/pages/__tests__/MyTrades.test.tsx` (new) (T10: `CardFilterBar` + status chips + buyer/seller tabs, tile grid via `TradeCard`)
- `frontend/src/pages/TradeMatchesPage.tsx`, `frontend/src/components/DuplicatesList.tsx`, `frontend/src/api/tradeMatch.ts`, `frontend/src/pages/__tests__/TradeMatchesPage.test.tsx` (T11: server-side duplicates filtering, client-side match filtering, slate palette, `gridClasses` prop)
- `frontend/src/pages/MyCollection.tsx` (T12: sticky filter bar swapped for `CardFilterBar`; state/URL logic untouched)

## Decisions
- Backend params on `/marketplace/listings` and `/trade/duplicates` are additive/optional with unchanged defaults (`name asc`; `quantity desc, name`), matching README decision #3 — no breaking change to existing callers.
- Route ordering respected: `/marketplace/listings/sets` and `/trade/duplicates/sets` declared ahead of their `{id}`-style siblings (README gotcha #4).
- MyCollection change (T12) is scoped to the sticky bar markup only; its own state/URL logic and existing test files were left untouched, per README decision #6.

## Notes for next Wave
- Backend subset (`tests/marketplace/test_router.py`, `tests/api/test_trade_match_router.py`) run green: 59 passed. Coverage-gate failure seen when running this subset alone (25.59% < 70%) is an artifact of running a partial suite, not a regression — full `pytest tests/ --cov=src` should be run for the real AC8 gate.
- All Wave 2 work (T07–T12) is still **uncommitted** in the worktree, same as Wave 1 flagged for Wave 2 — Wave 3 (T13/T14, diagrams + README) and TechLead/QA should commit/verify before building on top, and rerun the full frontend suite (`cd frontend && npm test`) to confirm the ≤13-pre-existing-failure gate (AC7) and the new `Marketplace.test.tsx`/`MyTrades.test.tsx`/`TradeMatchesPage.test.tsx` files pass.
- Frontend build (`npm run build`) and full `ruff check src/` were not run in this Wave-summary pass — still open for AC8 verification.
- `frontend/node_modules` shows as an untracked path in `git status` — confirm `.gitignore` covers it before any commit in Wave 3.

DIDIO_DONE: techlead wrote F174-wave-2-summary.md
