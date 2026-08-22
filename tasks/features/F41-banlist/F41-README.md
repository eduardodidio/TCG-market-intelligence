# F41 — Ban List (Lista de Banimentos)

**Status:** planned
**Created:** 2026-08-21

## Summary

Centralized ban list per format. Each card has a legality status per format
(legal, banned, restricted, suspended), an effective date, and a change
history. Data is synced from Scryfall's bulk legalities and stored locally
so the UI can filter, search, and cross-reference with the user's collection.

## User Story

As a Magic player, I want to see which cards are banned or restricted in each
format so I can verify my decks are legal and track ban list changes over time.

## Acceptance Criteria

1. **Data model**: `card_legalities` table stores (card_id, format, status,
   effective_date). `legality_history` table tracks every status change with
   old/new status and changed_at timestamp.
2. **Scryfall sync**: a CLI command (`banlist-sync`) and API trigger fetch
   legality data from Scryfall for all cards in the local DB, upsert
   `card_legalities`, and append diffs to `legality_history`.
3. **API endpoints**:
   - `GET /api/v1/banlist?format=X` — list banned/restricted cards for a format
   - `GET /api/v1/banlist/formats` — list all known formats
   - `GET /api/v1/banlist/card/{card_id}` — all legalities for a card
   - `GET /api/v1/banlist/history?format=X&card_id=Y` — change history
   - `POST /api/v1/banlist/sync` — trigger Scryfall sync (auth required)
4. **Frontend page**: `/banlist` route (public) with format dropdown filter,
   card list showing name + status + effective date, click-through to card
   detail. Search bar for card name. Status badges (banned=red,
   restricted=yellow, legal=green).
5. **Collection integration**: on the collection card detail page, show a
   "Legality" section listing the card's status per format.
6. **i18n**: all new UI strings have EN + PT-BR translations.
7. **Tests**: backend unit + integration tests for sync logic, repository,
   API endpoints. Frontend component tests for BanList page.

## Architecture

### Data Model

```
card_legalities
  id              INTEGER PK
  card_id         INTEGER NOT NULL  (FK to cards.id)
  format          VARCHAR(50) NOT NULL  (e.g. "standard", "modern", "legacy")
  status          VARCHAR(20) NOT NULL  (legal, banned, restricted, not_legal)
  effective_date  DATE NULL  (when this status took effect, NULL if unknown)
  updated_at      DATETIME
  UNIQUE(card_id, format)

legality_history
  id              INTEGER PK
  card_id         INTEGER NOT NULL
  format          VARCHAR(50) NOT NULL
  old_status      VARCHAR(20) NULL  (NULL on first insert)
  new_status      VARCHAR(20) NOT NULL
  changed_at      DATETIME NOT NULL
  source          VARCHAR(50) DEFAULT 'scryfall_sync'
  INDEX(card_id, format, changed_at)
```

### Scryfall Integration

- Use Scryfall API: `GET https://api.scryfall.com/cards/{set}/{number}`
  which includes a `legalities` object: `{"standard":"banned","modern":"legal",...}`
- Sync iterates all local cards (CardRow), fetches legality from Scryfall,
  upserts `card_legalities`, and if the status changed, appends to
  `legality_history`.
- Rate limit: Scryfall allows 10 req/s for non-bulk. For bulk sync, use
  Scryfall bulk data download (`default-cards` NDJSON) to avoid rate limits.
- CLI: `tcg banlist-sync [--bulk] [--limit N]`

### Backend

- New router: `src/api/routers/banlist.py`
- New schemas: `src/api/schemas/banlist.py`
- New domain models: `CardLegality`, `LegalityChange` in `src/domain/models.py`
- New DB models: `CardLegalityRow`, `LegalityHistoryRow` in `src/database/models.py`
- Repository methods: `upsert_legalities`, `get_legalities_by_format`,
  `get_legalities_for_card`, `get_legality_history`
- Sync orchestrator: `src/collectors/banlist_sync.py`

### Frontend

- New page: `frontend/src/pages/BanList.tsx`
- New API client: `frontend/src/api/banlist.ts`
- Route: `/banlist` (public, inside Layout)
- Nav link added to sidebar/header
- Legality badges component: `frontend/src/components/LegalityBadge.tsx`
- Legality section on `CollectionCardDetail.tsx`

## Constraints

- Scryfall rate limit: 10 req/s (use bulk download for full sync)
- Status values match Scryfall: `legal`, `not_legal`, `banned`, `restricted`
- Formats: standard, future, historic, timeless, gladiator, pioneer, explorer,
  modern, legacy, pauper, vintage, penny, commander, oathbreaker, standardbrawl,
  brawl, alchemy, paupercommander, duel, oldschool, premodern, predh
- effective_date is NULL on initial load (Scryfall does not provide it);
  future syncs populate it when a change is detected

## Tasks

| Task | File | Wave | Description |
|------|------|------|-------------|
| T01 | F41-T01.md | 0 | Data model: DB + domain models |
| T02 | F41-T02.md | 1 | Repository: legality CRUD methods |
| T03 | F41-T03.md | 1 | Scryfall sync orchestrator |
| T04 | F41-T04.md | 2 | API: banlist router + schemas |
| T05 | F41-T05.md | 2 | CLI: banlist-sync command |
| T06 | F41-T06.md | 3 | Frontend: API client + BanList page |
| T07 | F41-T07.md | 3 | Frontend: LegalityBadge + CollectionCardDetail integration |
| T08 | F41-T08.md | 4 | i18n + tests + diagrams |

## Waves

- **Wave 0** (1 task): T01 — DB migration + domain models (everything else depends on this)
- **Wave 1** (2 tasks, parallel): T02 (repository), T03 (sync orchestrator)
- **Wave 2** (2 tasks, parallel): T04 (API router), T05 (CLI command)
- **Wave 3** (2 tasks, parallel): T06 (frontend page), T07 (legality badges + detail integration)
- **Wave 4** (1 task): T08 (i18n, test gaps, diagrams)

## File Conflicts

- `src/database/models.py` — new tables (additive)
- `src/domain/models.py` — new dataclasses (additive)
- `src/database/repository.py` — new methods (additive)
- `src/cli/main.py` — new command (additive)
- `src/api/app.py` — register banlist router (one line)
- `frontend/src/App.tsx` — new route (additive)
- `frontend/src/pages/CollectionCardDetail.tsx` — add legality section
- `frontend/src/i18n/locales/en.json` — new keys
- `frontend/src/i18n/locales/pt-BR.json` — new keys
