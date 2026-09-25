# F173 — Wave 4 summary

**Status:** completed (staged, not yet committed)
**Tasks:** F173-T15
**Generated:** 2026-09-25T00:00:00Z

## Files touched
- `src/api/app.py` (T15: registers `meta_decks_router` under `/api/v1`, next to `news_router`)
- `src/cli/main.py` (T15: registers `collect_metagame_cmd` from `src.cli.metagame`)
- `frontend/src/i18n/locales/pt-BR.json` / `en.json` (T15: new `metaDecks` block + `topDecks.tabMine`/`tabMeta`/`viewMeta`)
- `bats/collect-metagame.bat` (T15: recreated — T12 never actually committed it since `bats/` is gitignored)
- `.gitignore` (T15: added `data/cache/`)
- `README.md` (T15: new "Top Decks do mercado (F173)" section — endpoints, CLI command, bat, UI route, ADR link)
- `tests/api/test_meta_decks_registration.py`, `tests/cli/test_cli_metagame_registration.py` (T15: new registration tests)

## Decisions
- `bats/collect-metagame.bat` was missing despite T12 being marked done (bats/ is gitignored, nobody used `git add -f`); Wave-4 dev recreated it from the T12 spec and it must be staged with `git add -f bats/collect-metagame.bat`.
- i18n also picked up `metaDecks.title`, `metaDecks.format.*` (7 keys), `metaDecks.board.*` (3 keys) beyond what T11's header comment listed, since `TopDecksPage.tsx` and dynamic key usage needed them.

## Notes for next Wave (TechLead review)
- Nothing is committed yet — `.gitignore`, `README.md`, `bats/collect-metagame.bat`, both locale files, `src/api/app.py`, `src/cli/main.py`, and both new registration tests are all currently staged only.
- Backend full suite: 116 failed / 5385 passed, 92.25% coverage — all 116 failures are pre-existing and unrelated to F173 (liga URL/provider, marketplace repo, collection, currency, error_codes); verified via before/after stash diff. `ruff check src/` clean.
- Frontend: 18 pre-existing failures across 12 unrelated files (Layout, OfflineBanner, DeckList, Login, MyTrades, etc.), verified as pre-existing via stash diff on the locale files. `npm run build` passes.
- New F173 registration tests (8) all pass.
