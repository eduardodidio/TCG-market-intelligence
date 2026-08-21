# F23 -- Deck Import

**Status:** planned
**Depends on:** F22 (Authentication)

## Summary

Allow users to import decks from a text or CSV list, view deck contents
with visual ownership indicators (darkened overlay for cards not in
collection), and navigate to card detail pages. Decks are per-user
(requires F22 auth).

## Architecture Impact

- `src/database/models.py` -- new `DeckRow` and `DeckCardRow` tables
- `src/database/repository.py` -- CRUD for decks + ownership query
- `src/domain/models.py` -- new `DeckSummary`, `DeckCardDetail` dataclasses
- `src/decks/parser.py` -- **new file**, text-format deck list parser
- `src/decks/importer.py` -- **new file**, deck import orchestrator (text + CSV)
- `src/api/schemas/decks.py` -- **new file**, Pydantic schemas
- `src/api/routers/decks.py` -- **new file**, deck CRUD endpoints
- `src/api/app.py` -- register decks router
- `frontend/src/types/api.ts` -- new Deck types
- `frontend/src/api/decks.ts` -- **new file**, API client
- `frontend/src/pages/DeckList.tsx` -- **new file**, list of user decks
- `frontend/src/pages/DeckView.tsx` -- **new file**, deck card grid with ownership overlay
- `frontend/src/components/DeckCardTile.tsx` -- **new file**, card tile with ownership state
- `frontend/src/components/DeckImportModal.tsx` -- **new file**, import form
- `frontend/src/App.tsx` -- new routes `/decks`, `/decks/:id`
- `frontend/src/components/Layout.tsx` -- add "My Decks" nav item

## Wave Manifest

| Wave | Tasks              | Description                                     |
|------|--------------------|--------------------------------------------------|
| 0    | T01, T02           | DB models + domain models (parallel)             |
| 1    | T03                | Repository CRUD + ownership query (depends T01)  |
| 2    | T04, T05           | Text parser + deck importer (parallel)            |
| 3    | T06, T07           | API schemas + API endpoints (parallel after T03+T05) |
| 4    | T08, T09, T10      | Frontend: types/API client, deck list, deck view (sequential) |
| 5    | T11                | Diagrams + documentation                         |

## Global Acceptance Criteria

- [ ] Decks table persists per-user decks with name and timestamps
- [ ] Deck cards are linked to canonical cards when possible
- [ ] Text format parser handles `{qty} {name}` and `{qty} {name} [{set}]`
- [ ] CSV format reuses collection importer column mapping
- [ ] `POST /api/v1/decks/import` creates a deck from text or CSV
- [ ] `GET /api/v1/decks` lists user's decks with ownership %
- [ ] `GET /api/v1/decks/{id}` returns cards with `in_collection` flag
- [ ] `DELETE /api/v1/decks/{id}` removes deck and cards (cascade)
- [ ] Frontend deck view shows darkened overlay for non-owned cards
- [ ] Hover tooltip on non-owned cards: "Card nao esta na sua colecao"
- [ ] Click on any card navigates to detail page
- [ ] All existing tests pass
- [ ] New tests added for all layers (coverage >= 90%)
- [ ] README.md updated with F23 delivery notes

## Diagrams

- `docs/diagrams/F23-architecture.mmd` -- deck import data flow
- `docs/diagrams/F23-journey.mmd` -- user journey for importing and viewing decks
