# F42 — Ban Engine in My Collection

**Status:** planned
**Created:** 2026-08-21
**Depends on:** F41 (Banlist)

## Summary

Cross-reference the user's collection against `card_legalities` (from F41)
to surface banned, restricted, and recently-changed cards. Provides a
dedicated API endpoint, an alert banner on the collection page, per-card
ban indicators on tiles, a legality analysis section on the card detail
page, and highlights for recent ban-list changes (last 7/30 days).

## User Story

As a Magic player, I want my collection page to warn me when cards I own
are banned or restricted in any format, and I want to see which bans
changed recently, so I can react quickly to metagame shifts and avoid
playing illegal cards.

## Acceptance Criteria

1. **Backend service**: a `BanAnalyzer` pure-function module that, given a
   list of card_ids and a format filter, returns banned/restricted entries
   enriched with recent-change flags.
2. **API endpoint**: `GET /api/v1/collection/banned` (auth required) returns
   the user's banned/restricted collection cards, grouped by format, with
   `recently_changed` flag for cards whose status changed in the last N days
   (default 30, configurable via `?days=N`).
3. **Collection summary extension**: `GET /collection/summary` response
   includes `banned_count` and `recently_changed_count` fields.
4. **Frontend — ban alert banner**: on MyCollection page, a dismissible
   warning banner shows when the user owns banned/restricted cards (e.g.
   "3 cards in your collection are banned in at least one format").
5. **Frontend — card tile indicator**: `CollectionCardTile` shows a small
   red "BANNED" badge (corner overlay) when the card is banned in any
   tracked format.
6. **Frontend — card detail legality section**: `CollectionCardDetail`
   shows a "Format Legality" panel listing per-format status with colored
   badges, highlighting recently-changed statuses with a "NEW" chip.
7. **Frontend — recently changed highlight**: cards that had a ban status
   change in the last 7 days get a pulsing border or glow on their tile.
8. **i18n**: all new UI strings have EN + PT-BR translations.
9. **Tests**: backend unit tests for BanAnalyzer, API endpoint tests,
   frontend component tests for banner, badge, and legality section.

## Architecture

### Backend

The ban engine is a read-only cross-reference layer. It queries
`card_legalities` (F41) joined with `user_collection` to find the user's
banned/restricted cards. It also queries `legality_history` (F41) to flag
recent changes.

```
user_collection.card_id  -->  card_legalities.card_id
                              legality_history.card_id
```

#### New files
- `src/services/ban_analyzer.py` — pure functions:
  - `get_banned_collection_cards(repo, user_id, format?, days=30)` ->
    list of `BannedCollectionCard`
  - `get_ban_summary(repo, user_id)` -> `BanSummary`
  - `get_card_legalities_with_changes(repo, card_id, days=30)` ->
    list of `CardLegalityWithChange`

#### New schemas
- `src/api/schemas/ban_engine.py`:
  - `BannedCollectionCard` — card info + format + status + recently_changed
  - `BanSummary` — banned_count, restricted_count, recently_changed_count
  - `CardLegalityWithChange` — format, status, effective_date,
    recently_changed, change_date

#### Modified files
- `src/api/routers/collection.py` — add `GET /collection/banned` endpoint
- `src/api/schemas/collection.py` — extend `CollectionSummary` with
  `banned_count`, `recently_changed_count`
- `src/database/repository.py` — add query methods:
  - `get_banned_collection_cards(user_id, format?, statuses?)`
  - `get_collection_ban_summary(user_id)`
  - `get_card_legalities_with_history(card_id, days)`

### Frontend

#### New files
- `frontend/src/api/banEngine.ts` — `fetchCollectionBanned()`,
  `fetchCardLegalities(cardId)`
- `frontend/src/components/BanAlertBanner.tsx` — dismissible warning banner
- `frontend/src/components/BanBadge.tsx` — small corner badge for tiles
- `frontend/src/components/LegalityPanel.tsx` — format legality grid with
  change highlights (uses `LegalityBadge` from F41)

#### Modified files
- `frontend/src/pages/MyCollection.tsx` — add BanAlertBanner above grid
- `frontend/src/pages/MyCollection.tsx` — pass ban status to
  CollectionCardTile (BanBadge overlay)
- `frontend/src/pages/CollectionCardDetail.tsx` — add LegalityPanel section
- `frontend/src/types/api.ts` — add ban engine types
- `frontend/src/i18n/locales/en.json` — new keys (~20)
- `frontend/src/i18n/locales/pt-BR.json` — new keys (~20)

## Constraints

- F41 must be implemented first (tables + sync must exist).
- Ban engine is read-only; it never writes to `card_legalities`.
- Only cards with `card_id IS NOT NULL` (linked cards) can be checked.
- Performance: the `/collection/banned` endpoint should use a single SQL
  join query, not N+1 per card.

## Tasks

| Task | File | Wave | Description |
|------|------|------|-------------|
| T01 | F42-T01.md | 0 | Repository: ban-related query methods |
| T02 | F42-T02.md | 1 | Service: BanAnalyzer + API schemas |
| T03 | F42-T03.md | 1 | API: /collection/banned endpoint + summary extension |
| T04 | F42-T04.md | 2 | Frontend: API client + TypeScript types |
| T05 | F42-T05.md | 2 | Frontend: BanAlertBanner + BanBadge components |
| T06 | F42-T06.md | 3 | Frontend: LegalityPanel on CollectionCardDetail |
| T07 | F42-T07.md | 3 | Frontend: wire banner + badges into MyCollection |
| T08 | F42-T08.md | 4 | i18n + tests + diagrams |

## Waves

- **Wave 0** (1 task): T01 — repository query methods (everything else depends on DB access)
- **Wave 1** (2 tasks, parallel): T02 (BanAnalyzer service), T03 (API endpoint)
- **Wave 2** (2 tasks, parallel): T04 (frontend API client), T05 (UI components)
- **Wave 3** (2 tasks, parallel): T06 (card detail integration), T07 (collection page integration)
- **Wave 4** (1 task): T08 (i18n, test gaps, diagrams)

## File Conflicts

- `src/database/repository.py` — new methods (additive)
- `src/api/routers/collection.py` — new endpoint (additive)
- `src/api/schemas/collection.py` — extend CollectionSummary (minor edit)
- `frontend/src/pages/MyCollection.tsx` — add banner + badge props
- `frontend/src/pages/CollectionCardDetail.tsx` — add legality panel
- `frontend/src/types/api.ts` — new interfaces (additive)
- `frontend/src/i18n/locales/en.json` — new keys
- `frontend/src/i18n/locales/pt-BR.json` — new keys
