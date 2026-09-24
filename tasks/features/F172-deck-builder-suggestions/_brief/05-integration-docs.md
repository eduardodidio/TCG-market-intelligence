# 05 — Shared-file integration + docs

## Shared files touched by F172 (ONLY in Wave 4)

| File | Task | Exact change |
|---|---|---|
| `src/api/app.py` | T17 | 1 import next to the other router imports + `app.include_router(deck_suggestions_router, prefix="/api/v1")` next to `decks_router` (line ~378) |
| `src/cli/main.py` | T17 | 2 lines just before `if __name__ == "__main__":` → `from src.cli.deck_suggestions import process_deck_suggestions  # noqa: E402` + `cli.add_command(process_deck_suggestions)` |
| `bats/deck-suggestions.bat` | T17 | new file (see `03-claude-processor.md`) |
| `.env.example` | T17 | append a commented `# F172 deck suggestions` block with the `DECK_SUGGEST_*` vars and `ANTHROPIC_API_KEY=` (empty) |
| `README.md` | T17 | append `### F172 -- Montar Deck: fix + Sugestão de deck (2026-09-xx)` to the "Shipped" section + endpoints to "REST API → Endpoints" + command to "Commands" |
| `frontend/src/i18n/locales/en.json`, `pt-BR.json` | T18 | add the `deckBuild.*` (existing wizard keys, missing today) and `deckSuggest.*` namespaces |

Not touched: `frontend/src/App.tsx`, `frontend/src/components/Layout.tsx`, `src/database/models.py`.

## Docs (Wave 0 + Wave 3)

- PRD `docs/prd/F172-deck-builder-suggestions.md` (T01; follow `docs/prd/template.md`).
- ADR `docs/adr/00NN-deck-suggestion-queue-claude.md` (T01). Use the **next free number at write time**
  (0014 today; F171–F179 may also add ADRs, so run `ls docs/adr` just before writing). Decision: async queue +
  daily local processing with Claude CLI by default (it uses the user's local Claude login, and no key is needed in Render);
  opt-in HTTP API runner via httpx + `ANTHROPIC_API_KEY`; no SDK dependency; the table is created from its own module
  (`checkfirst`) to avoid editing `models.py` in a parallel batch.
- Diagrams (T16): `docs/diagrams/F172-architecture.mmd`, `docs/diagrams/F172-journey.mmd` (templates in
  `docs/diagrams/templates/`).
