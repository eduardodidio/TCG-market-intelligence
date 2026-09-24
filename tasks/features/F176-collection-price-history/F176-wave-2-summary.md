# F176 — Wave 2 summary

**Status:** completed
**Tasks:** F176-T06, F176-T07, F176-T10
**Generated:** 2026-09-24T15:30:00Z (approximate — based on task file Status=done + checkpoint/log timestamps 15:02–15:14)

## Files touched
- `src/collectors/liga_sweep.py` (T06: `LigaSweepResult.daily_snapshot_created`, `run_liga_sweep(..., snapshot_after: bool = True)` calls `run_daily_snapshot` after `on_complete`, best-effort/never raises)
- `tests/collectors/test_liga_sweep_daily_snapshot.py` (N) (T06)
- `tests/collectors/test_liga_sweep.py` (T06: autouse fixture patches `run_daily_snapshot` to isolate existing call-count assertions)
- `src/services/collection_price_history.py` (N) (T07: `load_series`, `first_real_observation`, `build_history`; 1 query for series + 1 `MIN()` query for first real observation; foil isolation, 1 pt/day merge, `meta` dict)
- `tests/services/test_collection_price_history.py` (N, 21 tests, 100% coverage on the new module) (T07)
- `frontend/src/components/PriceHistoryMeta.tsx` (N) (T10: variant badge, sources list, "since" date, real-vs-snapshot counts)
- `frontend/src/components/PriceChart.tsx` (T10: renders `PriceHistoryMeta` when `meta` present, split empty states `empty-history-never`/`empty-history-period`, snapshot tooltip line, `ChartTooltip` now exported)
- `frontend/src/types/api.ts` (T10: `PriceHistoryMeta` interface, additive)
- `frontend/src/i18n/locales/en.json`, `frontend/src/i18n/locales/pt-BR.json` (T10: new top-level `priceHistory` block, incl. extra key `variantLabel` not in the brief)
- `frontend/src/components/__tests__/PriceHistoryMeta.test.tsx`, `frontend/src/components/__tests__/PriceChart.test.tsx` (N) (T10)

## Decisions
- T07: `resolve_history_keys` (T03) does not emit `daily_snapshot_backfill` keys, so `build_history` adds one next to each `daily_snapshot` key itself (`_with_backfill_keys`). Both count as snapshots in `meta`. Backfill currently falls back to `UNKNOWN_SOURCE_PRIORITY` (5) instead of a proper priority because T03's `SOURCE_PRIORITY` table doesn't list `daily_snapshot_backfill` — **follow-up needed**: add `"daily_snapshot_backfill": 9` to `price_history_keys.SOURCE_PRIORITY` (currently harmless since backfill never shares a day with a real `daily_snapshot`, but it's a latent gap Wave 3/4 or a fast-follow should close).
- T10: when `meta` is present, the legacy `no-data-for-period` line is hidden in favor of the new `empty-history-never`/`empty-history-period` states, to avoid duplicate/contradictory empty-state text. Without `meta` (old backend), behavior is unchanged — confirms backward compatibility (AC per T10).
- T10 added an untracked-in-brief i18n key `priceHistory.variantLabel` for the badge's `aria-label` — additive, no conflict.

## Notes for next Wave
- Wave 2 files are **not yet git-committed** (`git status --short` shows `src/collectors/liga_sweep.py`, all `frontend/*` T10 files, and the new `src/services/collection_price_history.py` / test files as modified/untracked). Wave 1 was committed (`1f534c3 F176 Wave 1`); Wave 2 should be committed before or at the start of Wave 3.
- Wave 3 (T08 `collection.py` history/metrics endpoints, T09 `cards.py` history endpoint) can now call `collection_price_history.build_history(repo, card_id, is_foil, days, today=None)` directly — it returns `(list[HistoricalPrice], meta_dict)` ready to feed into the `PriceHistoryMeta` schema (T04) and the observation `source` field.
- T09/T08 devs: `build_history`'s `meta["sources"]` already includes `daily_snapshot_backfill` deduplicated with `daily_snapshot` on the frontend side (T10), but the backend `meta.sources` list itself does **not** collapse the two — check whether T08/T09 or the schema layer needs to dedupe before AC10's "sources list" is rendered, or leave dedup to the frontend as T10 already does.
- Per governance amendment #1, confirm before Wave 3 whether `diagnosis.md`'s "Post-merge drift" section still matches ADR 0017's Decision section — Wave 1 summary flagged this as unverified; still unverified after Wave 2 (out of scope for T06/T07/T10).
