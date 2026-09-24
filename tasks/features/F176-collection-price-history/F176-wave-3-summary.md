# F176 — Wave 3 summary

**Status:** completed
**Tasks:** F176-T08, F176-T09
**Generated:** 2026-09-24T15:40:00Z (approximate — based on checkpoint timestamps 15:22–15:29, not yet committed)

## Files touched
- `src/api/routers/collection.py` (T08: `get_card_metrics` and `get_collection_history` now call `build_history(repo, entry.card_id, is_foil_entry(entry.extras), days*2+30 / days)` instead of iterating `repo.get_source_cards_for_card` + `repo.get_price_series`; removed the "no source_cards → empty" early return; `get_collection_history` adds `meta=PriceHistoryMeta(**meta)` to `CollectionHistoryResponse` and `source=p.source` on each `PriceObservation`)
- `src/api/routers/cards.py` (T09: `get_history` now calls `build_history(repo, card_id, is_foil=False, days)`, removed the source_cards early-return, adds `meta` and `PriceObservation.source`)
- `tests/api/test_collection_history_resolver.py` (N) (T08: normal/foil isolation, same-day liga+myp merge, manual priority, period=1y, invalid period 422, other-user 404, `card_id=None`, no-price card, currency conversion, metrics data_points)
- `tests/api/test_cards_history_resolver.py` (N) (T09: Liga-only, foil/normal isolation, Liga-beats-MYP same-day, manual priority, 404/422, no-price card)
- `tests/api/test_metrics_endpoint.py` (T08: fixtures/assertions updated to match `build_history`-based metrics response, replacing the old `source_cards`-early-return expectations)

## Decisions
- T08: `get_card_metrics` picks `all_prices[0].source`/`external_id` (fallback `"liga"`/`""` when empty) instead of the old "first source_card" — needed because `build_history` returns merged `HistoricalPrice` points, not source_card rows.
- T09: kept `get_history`'s foil always `False` (normal-variant contract), per T09's scope — matches AC9's "cards page shows normal variant" requirement.
- T09 dev flagged a **pre-existing, out-of-scope** failure: `tests/api/test_cards_router.py::TestGetHistory::test_specific_period` fails both before and after this change, because it hardcodes `observed_at=date(2026, 8, 12)` inside a `period=30d` window assertion that no longer holds against the environment's current date (2026-09-24, ~43 days later). Left unfixed and documented rather than touched, since it's unrelated to the Liga/meta contract T09 owns.
- T08's task file header still says `Status: planned` despite the implementation being present in `collection.py` and covered by `test_collection_history_resolver.py` — looks like a bookkeeping miss the developer didn't update; T09's header correctly says `Status: done`.

## Notes for next Wave
- **Nothing from Wave 3 is committed yet.** `git status --short` shows `src/api/routers/cards.py`, `src/api/routers/collection.py`, `tests/api/test_metrics_endpoint.py`, and `tasks/features/F176-collection-price-history/F176-T09.md` as modified, plus `tests/api/test_collection_history_resolver.py` and `tests/api/test_cards_history_resolver.py` as untracked. Wave 2 (`da9293f`) is committed; Wave 3 should be committed before or at the start of Wave 4.
- Verified locally: `pytest tests/api/test_collection_history_resolver.py tests/api/test_cards_history_resolver.py tests/api/test_metrics_endpoint.py -q` → 31 passed (coverage-gate failure in that run is only because the subset run doesn't hit 70% total repo coverage — not a real regression).
- Wave 2's open item about `daily_snapshot_backfill` missing an entry in `price_history_keys.SOURCE_PRIORITY` (falls back to `UNKNOWN_SOURCE_PRIORITY`) was **not** addressed in Wave 3 — still a latent gap for a fast-follow, per Wave 2's summary.
- Before Wave 4 (T11 shared files, T12 integration test), fix or explicitly carry forward: (1) T08's task-file `Status: planned` header, (2) the pre-existing `test_specific_period` date-drift failure in `tests/api/test_cards_router.py` (unrelated to F176 but will still show as a failure in a full `pytest tests/api` run T12/QA might do).
- Per governance amendment #1, the "Post-merge drift" cross-check between `diagnosis.md` and ADR 0017 is still unverified as of Wave 3 (flagged unresolved in Waves 1 and 2 as well) — Wave 4 or the TechLead review should close this before promotion.
