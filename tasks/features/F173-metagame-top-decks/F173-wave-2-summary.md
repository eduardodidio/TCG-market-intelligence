# F173 — Wave 2 summary

**Status:** completed
**Tasks:** F173-T07, F173-T08, F173-T09, F173-T10, F173-T11
**Generated:** 2026-09-24T22:00:00Z

## Files touched
- `src/metagame/sources/edhrec.py` (T07: `EdhrecSource.fetch_top_decks`, pure parsers, ranks kept even when a decklist fetch fails)
- `src/metagame/sources/mtgtop8.py` (T08: `Mtgtop8Source` for constructed formats, meta-page/archetype/decklist parsing, share parsing, 7-day decklist TTL)
- `src/metagame/collector.py` (T09: `MetagameCollector` — resolves cards before `replace_snapshot`, per-format error isolation, resolver cache keyed by name+set+number)
- `src/api/routers/meta_decks.py` (T10: `GET /api/v1/meta-decks`, `/formats`, `/{id}` detail with `price_brl`/`owned_qty`; must be registered before the SPA catch-all in T15)
- `frontend/src/components/meta/MetaDecksPanel.tsx`, `MetaFormatPills.tsx`, `MetaDeckRow.tsx`, `MetaDeckCardList.tsx` + `__tests__/*` (T11: format pills, lazy per-row detail fetch with AbortSignal, empty/error/loading states)
- Tests: `tests/unit/metagame/test_source_edhrec.py`, `tests/unit/metagame/test_source_mtgtop8.py`, `tests/unit/metagame/test_collector.py`, `tests/api/test_meta_decks_router.py` (all new)

## Decisions
- EDHREC (T07) and MTGTop8 (T08) both leave gaps in `rank` when a deck/archetype is skipped (failed decklist fetch) rather than renumbering — ranks reflect original meta position.
- Collector (T09) resolves all cards itself before writing the snapshot, keyed by `(external_id, card.name)`, so `unresolved_cards` is populated even in `dry_run`.
- Router (T10) tests build a minimal `FastAPI()` instead of `create_app()`, because `create_app()`'s SPA catch-all would shadow the router — this is now a hard constraint for T15's registration order in `app.py`.

## Notes for next Wave
- T15 **must** register `meta_decks` router in `src/api/app.py` before the `/{path:path}` SPA catch-all, or routes will 404 behind it.
- `edhrec.py` currently has ruff E501 warnings (noted by T08 dev); T12/T15 should run `ruff check src/` and clean this up before final gate.
- i18n keys needed by `MetaDecksPanel.tsx` are listed in a comment at the top of that file — T15 must add them to `pt-BR.json`/`en.json`.
- Resolver cache key change in T09 (`(name, set_code, collector_number)`) should be checked against T03's `MetagameRepository` schema for consistency in later QA.

## Retrospective Seeds
- **Pattern:** Router tests bypass `create_app()` because it mounts an SPA catch-all that shadows routers included after it — this constraint will recur for any future router that must be added to `src/api/app.py`.
- **Role(s) affected:** developer, techlead
- **Lesson:** When reviewing/adding a new router in `app.py`, check registration order against the SPA catch-all mount, not just the router's own tests.
