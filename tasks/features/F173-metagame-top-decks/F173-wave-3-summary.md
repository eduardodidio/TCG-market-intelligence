# F173 — Wave 3 summary

**Status:** completed
**Tasks:** F173-T12, F173-T13, F173-T14
**Generated:** 2026-09-24T22:10:00Z

## Files touched
- `src/cli/metagame.py` (new, T12: `collect_metagame_cmd` click command; not yet registered in `src/cli/main.py`, that's T15)
- `bats/collect-metagame.bat` (new, T12: weekly-run wrapper, LF line endings to match repo convention; gitignored dir, staged with `-f`)
- `src/metagame/sources/__init__.py` (edited, T12: populated `SOURCE_FOR_FORMAT` + `get_sources(fetcher)` registry)
- `tests/cli/test_cli_metagame.py` (new, T12)
- `tests/unit/metagame/test_http.py` (edited, T12: `test_registry_empty` replaced with `test_registry_populated` now that the registry is filled)
- `frontend/src/pages/TopDecksPage.tsx` (edited, T13: `view=mine|meta` + `format` query params; existing body extracted into internal `MyDecksRanking`, mounted only for `view=mine` so `fetchDeckRanking` never runs under `view=meta`; renders `MetaDecksPanel` for `view=meta`)
- `frontend/src/components/TopDecksPreview.tsx` (edited, T13: added `data-testid="top-decks-preview-meta-link"` to `/decks/ranking?view=meta`)
- `frontend/src/pages/__tests__/TopDecksPage.test.tsx` (new, T13, 8 tests)
- `frontend/src/components/__tests__/TopDecksPreview.test.tsx` (new, T13, 2 tests)
- `docs/diagrams/F173-architecture.mmd` (new, T14)
- `docs/diagrams/F173-journey.mmd` (new, T14)

## Decisions
- T12 used LF (not CRLF) for `bats/collect-metagame.bat` after checking that `bats/process-queue.bat` is already LF in this repo, overriding the task file's CRLF suggestion.
- T12's `--no-cache` is implemented as a `PoliteFetcher` subclass forcing `use_cache=False` on reads (writes still refresh cache); `src/metagame/http.py` itself was left unchanged.
- T13 kept `/decks/ranking` route unchanged (no new route) — `view`/`format` are query params, per plan; existing `mine` behavior is byte-for-byte preserved via the extracted `MyDecksRanking` subcomponent.

## Notes for next Wave
- **Registry test conflict (already resolved by T12, verify on integration):** T14's dev notes flagged that `test_http.py::test_registry_empty` would fail once T12 populates the registry — T12 did update that test to `test_registry_populated`. T15 should just confirm `pytest tests/unit/metagame -q` is fully green after all Wave 3 changes land together.
- T15 still owns: registering `collect_metagame_cmd` in `src/cli/main.py`, wiring the meta-decks router in `src/api/app.py`, adding i18n keys (`topDecks.tabMine`, `topDecks.tabMeta`, `topDecks.viewMeta`, `metaDecks.*`) to `pt-BR.json`/`en.json`, and README update.
- Pre-existing `npm test` baseline has 17 unrelated failures (UpdatePrompt import, legacy `*-error` testids, Layout, OfflineBanner) confirmed on a clean worktree before Wave 3 — Wave 3 adds no new frontend test failures; `npm run build` passes.
- Nothing in Wave 3 has been committed yet (working tree has the T12–T14 changes as uncommitted/untracked files) — a "F173 Wave 3" commit is still pending.
