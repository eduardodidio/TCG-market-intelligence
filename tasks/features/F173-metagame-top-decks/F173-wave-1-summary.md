# F173 — Wave 1 summary

**Status:** completed
**Tasks:** F173-T03, F173-T04, F173-T05, F173-T06
**Generated:** 2026-09-24T21:50:00Z

## Files touched
- `src/metagame/models.py` (T03: `MetaDeckRow`/`MetaDeckCardRow` SQLAlchemy models on shared `Base`)
- `src/metagame/repository.py` (T03: `MetagameRepository` — replace_snapshot, list_decks, get_deck_cards, owned_quantities, resolve_card_id)
- `tests/unit/metagame/test_repository.py` (T03: repository test suite)
- `src/metagame/http.py` (T04: `PoliteFetcher` — robots.txt, per-host rate limit, disk cache, tenacity retry)
- `src/metagame/sources/base.py` (T04: `MetaSource` Protocol, `MetaCardEntry`/`MetaDeckEntry`, `normalize_colors`)
- `src/metagame/sources/__init__.py` (T04: empty `SOURCE_FOR_FORMAT`/`get_sources` registry, populated later by T12)
- `tests/unit/metagame/test_http.py` (T04: fetcher test suite, `httpx.MockTransport`, fake clock/sleep)
- `src/metagame/valuation.py` (T05: pure `value_meta_deck` / `MetaDeckValuation`, no DB imports)
- `tests/unit/metagame/test_valuation.py` (T05: valuation test suite)
- `frontend/src/types/metaDecks.ts` (T06: `META_FORMATS`, `MetaDeckSummary`/`Detail`/`Card`, `MetaFormatsResponse`)
- `frontend/src/api/metaDecks.ts` (T06: `fetchMetaFormats`/`fetchMetaDecks`/`fetchMetaDeck`, AbortSignal-aware)
- `frontend/src/api/__tests__/metaDecks.test.ts` (T06: API client test suite)
- `src/metagame/sources/.gitkeep` deleted (T04: directory now holds real files)

## Decisions
- T03: card id resolution happens **before** the write transaction opens (nested Session on SQLite `:memory:` rolled back pending inserts otherwise). `replace_snapshot` accepts either a `card_ids` map or a `resolver` callable, falling back to `self.resolve_card_id`.
- T04: added an extra injectable `wall_clock` (separate from the monotonic `clock`) so on-disk cache timestamps survive process restarts; fetch order is cache → robots → rate limit → request.
- T05: baseline valuation rule is `total_value_brl = None` when no non-basic card is priced, except an all-basics deck which values at `0.00`.
- T06: added `MetaFormatsResponse` wrapper type (`/formats` returns an object, not a bare array) beyond what the task file specified.

## Notes for next Wave
- T03 flags a known limitation inherited from `_find_card_id`: name-only resolution returns `None` when a name has multiple printings unless set/collector number is given — T05/T10 (T09 collector, T10 router) valuation may want a name-based price fallback; TechLead should weigh in.
- T09 (Collector service, Wave 2) must not write to the DB from within resolvers — card id resolution must complete before `replace_snapshot`'s write transaction, per T03's note.
- `tests/unit/database/` has 50 pre-existing, unrelated SQLite FK failures (reproduce without this Wave's files) — not a regression from F173.
- Parallel Wave agents sharing `.coverage` in the worktree corrupts it; use a private `COVERAGE_FILE=...` per run for accurate coverage numbers.
- `src/metagame/sources/__init__.py` registry (`SOURCE_FOR_FORMAT`, `get_sources`) is intentionally empty — T12 populates it in Wave 3.
- Frontend: 13 test files / 17 tests fail on the base branch already (Layout, TopDecksPage, DeckList, Login, …), unrelated to F173; the new `metaDecks` suite passes 13/13.
