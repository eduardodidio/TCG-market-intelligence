# F33 — Historico de Precos (Price History Snapshots)

**Status:** planned
**Created:** 2026-08-21
**Dependencies:** F12 (JSON-LD Price Snapshot), F13 (Collection Scans)

## Summary

Enhance the price history system with period-based queries, data aggregation
for longer periods, a dedicated collection-card history endpoint, and an
upgraded frontend chart with 24h/7d/30d/90d/180d/1y period selector and
price change summary statistics.

## User Story

As a collector viewing a card's detail page, I want to select different time
periods (24h, 7d, 30d, 90d, 180d, 1y) and see the price history chart
update accordingly, with aggregated data points for longer periods so the
chart remains readable. I also want to see at a glance how the price changed
over my selected period (absolute and percentage change).

## Current State Analysis

### What Already Exists

1. **Database**: `price_observations` table stores daily snapshots with
   `source`, `external_id`, `observed_at`, `median_price`, `tcg_price`,
   `last_sold_price`, `quantity_available`, `currency`.

2. **Repository**: `get_price_series(source, external_id, days)` returns
   `HistoricalPrice` objects filtered by day count. Already supports
   list-of-sources and day filtering.

3. **API endpoints**:
   - `GET /cards/{card_id}/history?period=90d&currency=BRL` — returns raw
     `PriceObservation[]` for a card. Periods: 30d, 90d, 180d, 1y, 3y.
   - `GET /collection/{entry_id}` — returns `CollectionCardDetail` which
     includes `price_history: PriceObservation[]` (all-time, no period
     filter).

4. **Frontend**: `PriceChart` component with Recharts `LineChart`, period
   selector buttons (30d/90d/180d/1y/3y), drag-to-zoom, Brush slider.
   Calls `fetchCardHistory(cardId, period, currency)` via
   `GET /cards/{id}/history`.

5. **Analytics**: `src/analytics/indicators.py` has pure functions for
   moving averages, price extremes (ATH/ATL), volatility, and momentum.

### Gaps to Fill

1. **No 24h period**: current PERIOD_MAP starts at 30d. Need "24h" and "7d".
2. **No aggregation**: longer periods (180d, 1y) return every daily data
   point, making charts dense. Need weekly aggregation for 180d+ periods.
3. **Collection detail lacks period filter**: `GET /collection/{id}` always
   returns all-time history. The `PriceChart` component works around this
   by calling the cards endpoint, but this requires `card_id` and uses
   a different endpoint path.
4. **No price change summary**: the chart shows raw data but no
   delta/percentage change for the selected period.
5. **User default period**: no way to configure a preferred default period.

## Architecture

### Backend Changes

#### 1. Extend PERIOD_MAP (cards router)

Add `"24h": 1` and `"7d": 7` to the existing `PERIOD_MAP` in
`src/api/routers/cards.py`. The `HistoryPeriod` literal type in
`src/api/schemas/cards.py` also needs updating.

#### 2. Collection history endpoint

Add `GET /collection/{entry_id}/history?period=30d&currency=BRL` to
`src/api/routers/collection.py`. This mirrors the cards history endpoint
but takes a collection entry ID (with auth/ownership check) and resolves
to the linked card's source cards internally.

#### 3. Aggregation logic

Add `src/analytics/aggregation.py` with a pure function:

```
def aggregate_price_series(
    observations: list[PriceObservation],
    resolution: str,  # "daily" | "weekly"
) -> list[PriceObservation]:
```

- For "daily": pass-through (no change).
- For "weekly": group by ISO week, return one data point per week with
  the average of `median_price`, `tcg_price`, `last_sold_price`, and
  sum of `quantity_available`. Use the last date in each group as
  `observed_at`.

Apply automatically: periods <= 90d use daily resolution; 180d+ use weekly.

#### 4. Price change summary schema

Add `PriceChangeSummary` to `src/api/schemas/cards.py`:

```python
class PriceChangeSummary(BaseModel):
    period: str
    price_start: float | None
    price_end: float | None
    absolute_change: float | None
    percent_change: float | None
    data_points: int
    resolution: str  # "daily" | "weekly"
```

Add to history endpoint response alongside the observations list.

#### 5. User preferred period (optional, low priority)

Add `preferred_history_period` column to `users` table (default "30d").
Expose via `GET /auth/me` and `PATCH /auth/me/preferences`.

### Frontend Changes

#### 1. Update PriceChart period buttons

Add "24h" and "7d" to the `PERIODS` array. Update i18n keys.

#### 2. Price change summary display

Show above/below the chart: start price, end price, absolute change,
percent change (green/red coloring), resolution indicator.

#### 3. Collection detail: use collection history endpoint

Update `CollectionCardDetail.tsx` to call the new collection history
endpoint (`/collection/{id}/history`) instead of the cards endpoint.
This simplifies the data flow (no need to pass `card_id` separately).

#### 4. i18n keys

Add keys for new periods ("24h", "7d"), price change labels, resolution
indicator text.

### No Database Schema Changes

The existing `price_observations` table already stores daily snapshots.
Aggregation is computed at query time. The only schema change is the
optional `preferred_history_period` column on `users`.

## Acceptance Criteria

1. Period selector shows 6 options: 24h, 7d, 30d, 90d, 180d, 1y
2. Selecting a period fetches and displays data for that period only
3. Periods >= 180d aggregate to weekly resolution (fewer chart points)
4. Price change summary shows start/end price, absolute and % change
5. Collection card detail page uses dedicated collection history endpoint
6. All new code has unit tests (backend and frontend)
7. i18n keys added for both EN and PT-BR
8. Existing chart features (zoom, Brush, sparse-data notice) still work

## Constraints

- No new database tables or columns (except optional user preference)
- Aggregation is computed at query time, not stored
- Weekly aggregation uses ISO week grouping (Monday start)
- 24h period may return 0-1 data points; handle gracefully in UI

## Tasks

| Task | File | Wave | Description |
|------|------|------|-------------|
| T01 | F33-T01.md | 1 | Backend: extend periods + aggregation logic |
| T02 | F33-T02.md | 1 | Backend: collection history endpoint + price change summary |
| T03 | F33-T03.md | 2 | Frontend: updated PriceChart + price change summary |
| T04 | F33-T04.md | 2 | Frontend: collection detail integration + i18n |
| T05 | F33-T05.md | 3 | Tests: backend + frontend test coverage |

## Waves

- **Wave 1** (2 tasks, parallel): T01 (aggregation logic + extended periods),
  T02 (collection history endpoint + summary schema)
- **Wave 2** (2 tasks, parallel): T03 (PriceChart UI), T04 (collection detail
  wiring + i18n)
- **Wave 3** (1 task): T05 (comprehensive tests for all new code)

## File Conflicts

- `src/api/routers/cards.py` — T01 modifies PERIOD_MAP
- `src/api/routers/collection.py` — T02 adds new endpoint
- `src/api/schemas/cards.py` — T01 modifies HistoryPeriod, T02 adds
  PriceChangeSummary (T01 first, T02 second — no conflict if T01 lands first)
- `frontend/src/components/PriceChart.tsx` — T03 only
- `frontend/src/pages/CollectionCardDetail.tsx` — T04 only
- No cross-wave file conflicts
