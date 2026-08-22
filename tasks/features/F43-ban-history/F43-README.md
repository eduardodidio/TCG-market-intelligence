# F43 — Historico de Banimentos (Ban History)

**Status:** planned
**Created:** 2026-08-21
**Dependencies:** F41 (Banlist)

## Summary

Surface the legality change history created by F41 with dedicated API
endpoints, a ban history timeline page, price impact analysis stubs, and
a ban history section on the card detail page. F41 stores the raw data
(legality_history table with old/new status, changed_at, source). F43
makes that data queryable, visualizable, and lays the groundwork for
future market impact analysis.

## User Story

As a Magic player and market analyst, I want to browse a chronological
timeline of ban/unban events across formats, see the full ban history
for any specific card, and eventually understand how bans affect card
prices, so I can make informed trading decisions.

## Acceptance Criteria

1. **API - paginated history**: `GET /api/v1/banlist/history` endpoint
   (already planned in F41-T04) is extended with date range filtering
   (`date_from`, `date_to`), pagination metadata (total count), and
   card image URLs in the response.
2. **API - card ban history**: `GET /api/v1/banlist/history/{card_id}`
   returns the full chronological ban/unban history for a single card,
   across all formats.
3. **API - price impact stub**: `GET /api/v1/banlist/impact/{card_id}`
   returns a `BanImpactAnalysis` with price_before, price_after,
   percent_change for each ban event. Initially returns nulls for price
   fields (stub) with a `data_available: false` flag. Future features
   will populate this by cross-referencing price_observations.
4. **Frontend - ban history timeline page**: `/banlist/history` route
   showing a chronological feed of ban/unban events with format badges,
   status transition arrows (e.g. "legal -> banned"), card thumbnails,
   and date grouping. Filterable by format and date range.
5. **Frontend - card detail ban history section**: on
   `CollectionCardDetail.tsx`, below the legality grid (from F41-T07),
   add a "Ban History" collapsible section showing the card's timeline
   of status changes per format.
6. **Domain model**: `BanImpactAnalysis` dataclass with price snapshot
   fields (price_before, price_after, percent_change, window_days).
7. **i18n**: all new UI strings have EN + PT-BR translations.
8. **Tests**: backend unit + integration tests for new endpoints and
   impact stub. Frontend component tests for timeline and history section.

## Architecture

### Data Model

No new database tables. F43 builds on F41's `legality_history` table:

```
legality_history (from F41)
  id              INTEGER PK
  card_id         INTEGER NOT NULL
  format          VARCHAR(50) NOT NULL
  old_status      VARCHAR(20) NULL
  new_status      VARCHAR(20) NOT NULL
  changed_at      DATETIME NOT NULL
  source          VARCHAR(50) DEFAULT 'scryfall_sync'
  INDEX(card_id, format, changed_at)
```

### New Domain Models

Add to `src/domain/models.py`:

```python
@dataclass
class BanImpactAnalysis:
    """Price impact analysis for a single ban event."""
    card_id: int
    format: str
    old_status: str | None
    new_status: str
    changed_at: datetime
    window_days: int = 7          # look-back/forward window
    price_before: float | None = None  # avg price in window before ban
    price_after: float | None = None   # avg price in window after ban
    absolute_change: float | None = None
    percent_change: float | None = None
    data_available: bool = False   # False until price data is wired in
```

### New API Schemas

Add to `src/api/schemas/banlist.py`:

```python
class LegalityHistoryResponse(BaseModel):
    """Paginated history response with metadata."""
    items: list[LegalityHistoryEntry]
    total: int
    limit: int
    offset: int

class CardBanHistoryEntry(BaseModel):
    """Single ban event for the card history timeline."""
    id: int
    format: str
    old_status: str | None
    new_status: str
    changed_at: datetime
    source: str

class BanImpactSchema(BaseModel):
    """Price impact analysis for a ban event (stub)."""
    format: str
    old_status: str | None
    new_status: str
    changed_at: datetime
    window_days: int
    price_before: float | None
    price_after: float | None
    absolute_change: float | None
    percent_change: float | None
    data_available: bool
```

### API Endpoints

Extend `src/api/routers/banlist.py`:

1. **Enhance `GET /banlist/history`** (from F41-T04):
   - Add query params: `date_from: date | None`, `date_to: date | None`,
     `offset: int = 0`
   - Add `total` count to response (wrap in `LegalityHistoryResponse`)
   - Add `image_url` field to `LegalityHistoryEntry`

2. **`GET /banlist/history/{card_id}`** (new):
   - Returns `list[CardBanHistoryEntry]` for a specific card
   - All formats, ordered by changed_at DESC
   - Public endpoint

3. **`GET /banlist/impact/{card_id}`** (new, stub):
   - Returns `list[BanImpactSchema]` (one per ban event)
   - Initially returns all price fields as None, data_available=False
   - Query param: `window_days: int = 7` (for future use)
   - Public endpoint

### Repository

Add to repository (or extend F41's methods):

1. `get_legality_history_paginated(card_id, format, date_from, date_to, limit, offset) -> tuple[list[LegalityHistoryRow], int]`
   - Returns (rows, total_count) for paginated response
   - JOIN with cards for card name + image info

2. `get_card_ban_history(card_id: int) -> list[LegalityHistoryRow]`
   - All history rows for one card, all formats, ordered by changed_at DESC

3. `count_legality_history(card_id, format, date_from, date_to) -> int`
   - Count query for pagination metadata

### Frontend

1. **Ban history timeline page**: `frontend/src/pages/BanHistory.tsx`
   - Route: `/banlist/history` (public)
   - Chronological feed grouped by date (month/year headers)
   - Each event: card thumbnail, card name, format badge, status
     transition ("legal -> banned" with colored arrow), date
   - Filters: format dropdown, date range picker (month/year selectors)
   - Pagination: "Load more" button at bottom
   - Empty state when no history events exist

2. **API client**: extend `frontend/src/api/banlist.ts`
   - `fetchBanHistory(params)` -> paginated history
   - `fetchCardBanHistory(cardId)` -> card-specific history
   - `fetchBanImpact(cardId)` -> impact analysis (stub)

3. **Ban history section on card detail**:
   - Add to `CollectionCardDetail.tsx` below legality grid
   - Collapsible section "Ban History"
   - Vertical timeline of status changes per format
   - Empty state: "No ban history for this card"

4. **BanEventCard component**: `frontend/src/components/BanEventCard.tsx`
   - Reusable card for a single ban event
   - Shows: format badge, old_status -> new_status with arrow, date
   - Color-coded: ban events in red tones, unban in green tones

5. **StatusTransition component**: `frontend/src/components/StatusTransition.tsx`
   - Renders "legal -> banned" with colored badges and arrow
   - Reused in BanEventCard and card detail timeline

## Constraints

- No new database tables or columns
- Price impact endpoint is a stub (returns nulls) — actual price
  cross-referencing deferred to a future feature
- Depends entirely on F41 being implemented first (uses legality_history
  table + existing banlist router)
- Scryfall image URLs constructed client-side from set_code +
  collector_number (existing pattern)

## Tasks

| Task | File | Wave | Description |
|------|------|------|-------------|
| T01 | F43-T01.md | 0 | Domain model + API schemas |
| T02 | F43-T02.md | 1 | Repository: paginated history + card ban history |
| T03 | F43-T03.md | 1 | API: enhanced history endpoint + card history + impact stub |
| T04 | F43-T04.md | 2 | Frontend: BanEventCard + StatusTransition + API client |
| T05 | F43-T05.md | 2 | Frontend: BanHistory timeline page |
| T06 | F43-T06.md | 3 | Frontend: card detail ban history section + i18n + tests |

## Waves

- **Wave 0** (1 task): T01 — domain models + schemas (everything else depends on these)
- **Wave 1** (2 tasks, parallel): T02 (repository methods), T03 (API endpoints)
- **Wave 2** (2 tasks, parallel): T04 (shared components + API client), T05 (timeline page)
- **Wave 3** (1 task): T06 (card detail integration, i18n, test gaps, diagrams)

## File Conflicts

- `src/domain/models.py` — T01 adds BanImpactAnalysis (additive)
- `src/api/schemas/banlist.py` — T01 adds new schemas (additive, after F41)
- `src/database/repository.py` — T02 adds new methods (additive, after F41)
- `src/api/routers/banlist.py` — T03 extends router (after F41-T04)
- `frontend/src/api/banlist.ts` — T04 extends client (after F41-T06)
- `frontend/src/pages/CollectionCardDetail.tsx` — T06 adds section (after F41-T07)
- `frontend/src/i18n/locales/en.json` — T06 adds keys (additive)
- `frontend/src/i18n/locales/pt-BR.json` — T06 adds keys (additive)
- `frontend/src/App.tsx` — T05 adds route (additive)
