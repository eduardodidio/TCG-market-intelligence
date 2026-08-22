# F29 — Single Card Real-Time Refresh

**Status:** planned
**Created:** 2026-08-21

## Summary

Add a refresh button on every card display (collection grid, collection detail,
deck view) that fetches the card's current price from MYP in real-time and
updates the displayed data.

## User Story

As a collector, I want to refresh a single card's price data on demand so I can
see the most current market price without running a full collection scan.

## Architecture

### Backend

- New endpoint: `POST /api/v1/collection/{entry_id}/refresh` (auth required)
  - Looks up the collection entry + linked source card (external_id, slug)
  - Calls `MypCardsProvider.fetch_current_price(external_id, slug)`
  - If price returned, inserts a `jsonld_snapshot` observation via repository
  - Returns updated `CollectionCardDetail` with fresh price
  - If no source card linked, returns 422 (card not linked to MYP)

### Frontend

- New `refreshCard(entryId)` API function in `frontend/src/api/collection.ts`
- Refresh icon button on `CollectionCardTile` (collection grid) — small icon
  overlay, top-left or bottom-right
- Refresh button on `CollectionCardDetail` page — next to the price display
- Refresh button on `DeckCardTile` (deck view) — if card has a collection entry
- Loading spinner replaces the refresh icon during fetch
- On success: update the card's `latest_price` in local state
- On error: show brief toast/inline error

## Constraints

- Rate limit: reuse existing MYP provider delay (1s between requests)
- Only works for cards linked to a MYP source card (card_id != null)
- Button hidden/disabled for unlinked cards

## Tasks

| Task | File | Wave | Description |
|------|------|------|-------------|
| T01 | F29-T01.md | 1 | Backend: refresh endpoint |
| T02 | F29-T02.md | 1 | Frontend: API client function |
| T03 | F29-T03.md | 2 | Frontend: refresh button on CollectionCardDetail |
| T04 | F29-T04.md | 2 | Frontend: refresh button on CollectionCardTile |
| T05 | F29-T05.md | 2 | Frontend: refresh button on DeckCardTile |
| T06 | F29-T06.md | 3 | i18n keys + tests |

## Waves

- **Wave 1** (2 tasks, parallel): T01 (backend), T02 (frontend API)
- **Wave 2** (3 tasks, parallel): T03, T04, T05 (UI components)
- **Wave 3** (1 task): T06 (i18n + integration tests)

## File Conflicts

- `src/api/routers/collection.py` — new endpoint (additive, low risk)
- `frontend/src/pages/CollectionCardDetail.tsx` — add refresh button
- `frontend/src/pages/MyCollection.tsx` — modify CollectionCardTile
- `frontend/src/components/DeckCardTile.tsx` — add refresh button
