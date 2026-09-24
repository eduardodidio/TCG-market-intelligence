# F175 — Wave 1 summary

**Status:** partial
**Tasks:** F175-T03, F175-T04, F175-T05, F175-T06
**Generated:** 2026-09-24T13:00:00Z (UTC, approximate — no exact wave-start timestamp available)

## Files touched
- `src/database/trending_queries.py` (T03: new module, `load_market_trending_prices` unions `source_cards` + direct `liga_`/`manual_` price_observations via regex `parse_direct_card_id`)
- `src/database/repository.py` (T03: `get_trending_price_data` body replaced with delegation to `trending_queries`, 46 lines removed)
- `tests/unit/database/test_trending_queries.py` (T03: new regression tests)
- `src/services/trending.py` (T04: cache policy split — success 30 min, legit-empty 2 min, query-failed not cached; added `trending_computed` structured log)
- `tests/unit/services/test_trending_service_cache_f175.py` (T04: new cache-policy tests)
- `frontend/src/pages/__tests__/TrendingCollectionToggle.test.tsx` (T05: new toggle regression tests)
- `docs/diagrams/F175-architecture.mmd`, `docs/diagrams/F175-journey.mmd` (T06: new, validated with mermaid-cli)

## Decisions
- T03/T04 followed the brief exactly: card-id extraction done via Python regex `^(?:liga|manual)_(\d+)(?:_foil)?$` post-filter rather than SQL `LIKE`, to avoid `_` wildcard collisions.
- T06 diagrams were built from the task files (F175-README + T03/T04/T05), not from `_brief/`, because `_brief/00-overview.md` etc. do not exist in this checkout (only referenced from Dev Notes).

## Notes for next Wave
- **T03 and T05 are implemented on disk (files exist, diffs present) but their task files still say `Status: planned` and have no "Notes from Developer" section** — unlike T04/T06, which are `Status: done` with completion notes. Wave 2 (T07/T08 + TechLead review) should verify T03/T05 actually finished cleanly (run `pytest tests/unit/database/test_trending_queries.py`, `cd frontend && npx vitest run src/pages/__tests__/TrendingCollectionToggle.test.tsx`) before treating them as closed, and update their status/notes if confirmed done.
- Nothing from Wave 1 is committed yet — all changes are uncommitted (`git status` shows modified `repository.py`/`trending.py` and untracked new files). T07/T08 or a human should commit before Wave 2 review closes out.
- T05's task explicitly calls for a conditional fix in `TrendingSection.tsx`/`useApi.ts` if a race condition is found; `git status` shows neither file modified, so either no race was found or that check wasn't completed — worth confirming when reviewing T05.
