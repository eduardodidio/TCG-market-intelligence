# F35 — Top Decks por Valor (Top Decks by Value)

**Status:** planned
**Created:** 2026-08-21
**Dependencies:** F34 (History Metrics — planned)

## Summary

Rank decks by total value (sum of card prices) and show value evolution
over time. A new ranking endpoint exposes sortable/filterable deck
listings. The frontend gets a dedicated Top Decks page with ranked
list, value badges, change indicators, and sparkline value trends.

## User Story

As a collector, I want to see which of my decks are most valuable and
how their values have changed over time, so I can track my investment
and prioritize trades or purchases.

## Current State Analysis

### What Already Exists

1. **Deck storage** (`DeckRow`, `DeckCardRow`): decks belong to a user,
   deck cards link to canonical `card_id` via `DeckCardRow.card_id`.

2. **Deck API** (`src/api/routers/decks.py`): CRUD endpoints — import,
   list, detail (with per-card prices), delete. The detail endpoint
   already computes per-card `latest_price` via `get_latest_prices_batch`.

3. **Price data**: `PriceObservationRow` stores daily snapshots per
   source card. `Repository.get_latest_prices_batch(card_ids)` returns
   the most recent observation per card. `get_price_series(source,
   external_id, days)` returns historical prices.

4. **Analytics** (`src/analytics/indicators.py`): pure functions for
   moving averages, ATH/ATL, volatility, momentum. F34 adds
   `compute_performance_score` and `compute_period_comparison`.

5. **Currency conversion**: `CurrencyConverter` supports BRL/USD/PILA.
   Deck detail endpoint already applies conversion per card.

6. **Frontend deck pages**: `DeckList.tsx` (grid of deck summaries),
   `DeckView.tsx` (card grid with ownership overlay and per-card prices).
   Neither page shows total deck value or value change.

### Gaps to Fill

1. **No deck valuation service**: no function sums card prices into a
   deck total value. No historical deck value tracking.
2. **No ranking endpoint**: no way to sort/filter decks by value.
3. **No value change computation**: no delta or percent change for deck
   value over a period.
4. **No Top Decks page**: no frontend view for ranked deck listing.
5. **No sparkline data**: no endpoint returns a compact time series of
   deck value for sparkline rendering.
6. **DeckSummarySchema** lacks `total_value`, `value_change_pct` fields.

## Architecture

### Backend Changes

#### 1. Deck valuation service (`src/decks/valuation.py`)

Pure service module with functions:

- `compute_deck_value(card_prices: dict[int, Decimal | None],
  deck_cards: list[DeckCardRow]) -> DeckValuation`:
  Sum `card_price * quantity` for each deck card with a linked card_id
  and a known price. Returns `DeckValuation(total_value, priced_cards,
  unpriced_cards)`.

- `compute_deck_value_series(deck_cards, price_series_by_card, days)
  -> list[DeckValuePoint]`:
  For each date in the union of all cards' price series, sum all card
  prices at that date (carry-forward last known price for gaps).
  Returns `list[DeckValuePoint(date, total_value)]` for sparkline use.

- `compute_deck_value_change(value_series, period_days)
  -> DeckValueChange | None`:
  Compare current value to value `period_days` ago. Returns
  `DeckValueChange(current, previous, delta, delta_pct)`.

Domain dataclasses in `src/domain/models.py`:
- `DeckValuation(total_value, priced_cards, unpriced_cards)`
- `DeckValuePoint(date, total_value)`
- `DeckValueChange(current, previous, delta, delta_pct)`

#### 2. Repository helper

Add `Repository.get_price_series_batch(card_ids, days)` that returns
`dict[int, list[HistoricalPrice]]` — batch-loads price series for
multiple cards in one query (avoids N+1 for deck valuation).

#### 3. Ranking API endpoint

Add `GET /api/v1/decks/ranking` to `src/api/routers/decks.py`.

Query parameters:
- `sort_by`: `total_value` (default) | `value_change_pct` |
  `value_change_abs` | `card_count`
- `sort_order`: `desc` (default) | `asc`
- `period`: `7d` | `30d` | `90d` (default `30d`) — for value change
- `min_value`: float | None — minimum deck value filter
- `max_value`: float | None — maximum deck value filter
- `currency`: `BRL` | `USD` | `PILA` (default user preference)
- `limit`: int (default 20, max 100)
- `offset`: int (default 0)

Response schema `DeckRankingResponse`:
```python
class DeckRankingEntry(BaseModel):
    id: int
    name: str
    description: str | None
    total_cards: int
    unique_cards: int
    owned_cards: int
    ownership_pct: float
    total_value: float | None
    priced_cards: int
    unpriced_cards: int
    value_change: float | None       # absolute delta
    value_change_pct: float | None   # percent delta
    sparkline: list[float]           # last N values for mini chart
    currency: str
    created_at: datetime
    updated_at: datetime

class DeckRankingResponse(BaseModel):
    decks: list[DeckRankingEntry]
    total: int
    sort_by: str
    period: str
```

Implementation flow:
1. Load all user decks
2. For each deck, load deck cards and batch-fetch latest prices
3. Compute `DeckValuation` for each
4. If sorting by value change, compute `value_series` and `value_change`
5. Apply min/max value filters
6. Sort by requested field
7. Paginate and return

#### 4. Deck value detail endpoint

Add `GET /api/v1/decks/{deck_id}/value?period=30d&currency=BRL` to
return full value series for chart rendering on the deck detail page.

Response:
```python
class DeckValueDetailSchema(BaseModel):
    deck_id: int
    total_value: float | None
    priced_cards: int
    unpriced_cards: int
    value_change: float | None
    value_change_pct: float | None
    value_series: list[DeckValuePointSchema]
    currency: str
    period: str

class DeckValuePointSchema(BaseModel):
    date: str  # ISO date
    value: float
```

#### 5. Extend DeckSummarySchema

Add `total_value: float | None` and `value_change_pct: float | None`
to the existing `DeckSummarySchema` so the deck list page can show
value badges without a separate call.

### Frontend Changes

#### 1. Top Decks page (`TopDecksPage.tsx`)

New page at route `/decks/ranking`. Shows:
- Header with title and sort/filter controls
- Ranked list of deck cards (not card grid — list/table layout)
- Each row: rank number, deck name, total value (big, bold), value
  change badge (green/red arrow + percent), sparkline (tiny Recharts
  LineChart), card count, ownership %
- Sort dropdown: Value, Value Change %, Card Count
- Period selector: 7d / 30d / 90d
- Price range filter (optional, collapsible)

#### 2. Sparkline component (`DeckSparkline.tsx`)

Tiny inline Recharts `LineChart` (no axes, no grid, just the line).
Green if trending up, red if down. Accepts `data: number[]`.

#### 3. Value badge on DeckList

Update `DeckList.tsx` to show `total_value` and `value_change_pct`
from the extended `DeckSummarySchema`. Small badge with colored
change indicator.

#### 4. Value section on DeckView

Add a value summary panel at the top of `DeckView.tsx`: total deck
value, value change, and a value history chart (Recharts AreaChart
using the `/decks/{id}/value` endpoint data).

#### 5. Navigation

Add "Top Decks" link to sidebar/nav. Route: `/decks/ranking`.

#### 6. API client functions

Add to `frontend/src/api/decks.ts`:
- `fetchDeckRanking(params)` — calls `GET /api/v1/decks/ranking`
- `fetchDeckValue(deckId, period, currency)` — calls
  `GET /api/v1/decks/{id}/value`

#### 7. i18n keys

Add keys for: page title, sort options, period labels, value labels,
change indicators, empty states, filter labels.

## Acceptance Criteria

1. `GET /decks/ranking` returns decks sorted by total value (desc) with
   value, change, and sparkline data
2. Sorting by `value_change_pct` correctly ranks by appreciation/depreciation
3. `min_value` / `max_value` filters work correctly
4. Period parameter (7d/30d/90d) affects value change calculations
5. Currency conversion applies to all value fields
6. Sparkline data has at most 30 points (downsampled if needed)
7. `GET /decks/{id}/value` returns full value time series for chart
8. Frontend Top Decks page renders ranked list with sparklines
9. DeckList page shows value badges on each deck card
10. DeckView page shows value summary with trend chart
11. Graceful handling when cards have no price data (show "N/A", not 0)
12. All new backend code has unit tests (valuation service, endpoints)
13. All new frontend components have tests
14. i18n keys added for EN and PT-BR

## Constraints

- Depends on F34 shipping first (for period comparison patterns and
  analytics infrastructure)
- No new database tables — deck value is computed at query time from
  existing price_observations
- Valuation functions remain pure (no DB imports)
- Sparkline downsampled to max 30 points for performance
- Ranking endpoint limited to authenticated user's own decks

## Tasks

| Task | File | Wave | Description |
|------|------|------|-------------|
| T01 | F35-T01.md | 0 | Domain models for deck valuation |
| T02 | F35-T02.md | 1 | Backend: valuation service + repository helper |
| T03 | F35-T03.md | 1 | Backend: ranking + value detail API endpoints |
| T04 | F35-T04.md | 2 | Frontend: TopDecksPage + DeckSparkline + API client |
| T05 | F35-T05.md | 2 | Frontend: DeckList value badges + DeckView value panel |
| T06 | F35-T06.md | 3 | Frontend: navigation + i18n + integration |
| T07 | F35-T07.md | 4 | Tests: backend + frontend comprehensive coverage |

## Waves

- **Wave 0** (1 task): T01 — domain models (no dependencies, unblocks
  all other tasks)
- **Wave 1** (2 tasks, parallel): T02 (valuation service + repo),
  T03 (API endpoints + schemas). T03 imports T02 functions but both
  can be developed in parallel within the wave.
- **Wave 2** (2 tasks, parallel): T04 (Top Decks page + sparkline),
  T05 (DeckList badges + DeckView value panel). Independent pages.
- **Wave 3** (1 task): T06 — navigation wiring, i18n, final integration
- **Wave 4** (1 task): T07 — comprehensive test coverage

## File Inventory

### New Files
- `src/decks/valuation.py` — pure valuation functions (T02)
- `src/api/schemas/deck_ranking.py` — Pydantic schemas (T03)
- `frontend/src/pages/TopDecksPage.tsx` — ranking page (T04)
- `frontend/src/components/DeckSparkline.tsx` — sparkline component (T04)
- `frontend/src/api/deckRanking.ts` — API client functions (T04)
- `tests/unit/decks/test_valuation.py` — valuation tests (T07)
- `tests/unit/api/test_deck_ranking.py` — endpoint tests (T07)
- `frontend/tests/pages/TopDecksPage.test.tsx` — page tests (T07)
- `frontend/tests/components/DeckSparkline.test.tsx` — sparkline tests (T07)

### Modified Files
- `src/domain/models.py` — add DeckValuation, DeckValuePoint, DeckValueChange (T01)
- `src/database/repository.py` — add get_price_series_batch (T02)
- `src/api/routers/decks.py` — add ranking + value endpoints (T03)
- `src/api/schemas/decks.py` — extend DeckSummarySchema (T03)
- `frontend/src/types/api.ts` — add ranking types (T04)
- `frontend/src/pages/DeckList.tsx` — add value badges (T05)
- `frontend/src/pages/DeckView.tsx` — add value panel (T05)
- `frontend/src/App.tsx` — add /decks/ranking route (T06)
- `frontend/src/i18n/locales/en.json` — ranking i18n keys (T06)
- `frontend/src/i18n/locales/pt-BR.json` — ranking i18n keys (T06)

### No Cross-Wave File Conflicts
- Wave 0: `models.py` only (T01)
- Wave 1: `valuation.py` + `repository.py` (T02), `decks.py` router +
  schemas (T03) — no overlap
- Wave 2: `TopDecksPage.tsx` (T04), `DeckList.tsx` + `DeckView.tsx` (T05)
  — no overlap
- Wave 3: `App.tsx` + i18n files (T06) — no overlap with Wave 2
- Wave 4: test files only (T07)
