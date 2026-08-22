# F30 — Bulk Collection Price Refresh

**Status:** planned
**Created:** 2026-08-21

## Summary

Add a "Refresh All Prices" button on the collection page that triggers a scan
of all collection cards, showing real-time progress and updating prices as
results arrive.

## User Story

As a collector, I want to update all my collection card prices at once so I can
see the current total value of my collection without refreshing cards one by one.

## Architecture

### Backend

The scan infrastructure already exists (`POST /api/v1/scans` with `card_ids`
filter). The bulk refresh reuses this:
- Trigger a scan via existing `POST /api/v1/scans` with `scan_type=collection`
- Poll progress via existing `GET /api/v1/scans/{scan_id}`
- No new backend endpoints needed — reuse F13 scan system

### Frontend

- "Refresh All" button in MyCollection header area (next to GridSizeToggle)
- On click: `POST /api/v1/scans` with `scan_type=collection`
- Poll `GET /api/v1/scans/{scan_id}` every 3s for progress
- Show progress bar with `cards_processed / cards_total`
- Show status text: "Refreshing... 42/120 cards"
- On completion: re-fetch collection data to show updated prices
- Cancel button: frontend stops polling (scan continues server-side)
- Disable "Refresh All" while a scan is in progress
- AbortController for cleanup on unmount

## Constraints

- Reuses existing scan infrastructure (no new backend code)
- Progress is approximate (poll interval = 3s)
- MYP rate limiting applies (scan may take minutes for large collections)
- Only one scan at a time (UI enforced, not backend)

## Tasks

| Task | File | Wave | Description |
|------|------|------|-------------|
| T01 | F30-T01.md | 1 | Frontend: scan API client functions |
| T02 | F30-T02.md | 1 | Frontend: useCollectionRefresh hook (trigger + poll + progress) |
| T03 | F30-T03.md | 2 | Frontend: RefreshAllButton component + integration in MyCollection |
| T04 | F30-T04.md | 2 | i18n keys + tests |

## Waves

- **Wave 1** (2 tasks, parallel): T01 (API client), T02 (hook)
- **Wave 2** (2 tasks, parallel): T03 (UI integration), T04 (i18n + tests)

## File Conflicts

- `frontend/src/pages/MyCollection.tsx` — add RefreshAllButton in header
- `frontend/src/api/` — new scan client functions (additive)
- No backend changes needed
