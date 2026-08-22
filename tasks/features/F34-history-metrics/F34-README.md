# F34 — Metricas de Historico (History Metrics)

**Status:** planned
**Created:** 2026-08-21
**Dependencies:** F33 (Price History — must ship first)

## Summary

Add computed analytics metrics to the card detail experience. Using the
price snapshots already stored in `price_observations` and F33's
period-based history queries, compute and display: moving averages,
ATH/ATL, volatility, momentum/trend, and period-over-period performance
scores. Expose via a dedicated API endpoint and render as stats cards and
trend indicators on the collection card detail page.

## User Story

As a collector viewing a card, I want to see key financial metrics
(7-day/30-day moving average, all-time high/low, volatility, trend
direction, and a performance score) so I can make informed buy/sell
decisions without manual calculation.

## Current State Analysis

### What Already Exists

1. **Analytics engine** (`src/analytics/indicators.py`): pure functions
   for moving averages (7/30/90-day), price extremes (ATH/ATL with
   dates), volatility (std dev + coefficient of variation), and momentum
   (rate of change + trend direction "up"/"down"/"flat"). All operate on
   `list[HistoricalPrice]` and return domain dataclasses.

2. **Domain models** (`src/domain/models.py`): `MovingAverage`,
   `PriceExtremes`, `Volatility`, `Momentum`, `CardAnalytics` (composite
   orchestrator result). All use `Decimal` for price arithmetic.

3. **Orchestrator** (`compute_card_analytics()`): already assembles all
   indicators into a single `CardAnalytics` object given a price list,
   source, and external_id.

4. **Price data path**: `Repository.get_price_series(source, external_id,
   days)` returns `HistoricalPrice[]`. F33 adds period-based queries with
   aggregation and a `PriceChangeSummary` schema.

5. **Frontend**: `CollectionCardDetail.tsx` shows card info + PriceChart.
   No metrics display yet. `KpiCard` component exists on Dashboard.

### Gaps to Fill

1. **No API endpoint for metrics**: `compute_card_analytics()` exists but
   is not exposed via any REST endpoint.
2. **No period-scoped metrics**: existing functions compute over the full
   price list. Need to scope by period (e.g., 30d volatility, 7d trend).
3. **No performance score**: no composite "how is this card doing?"
   indicator. Need a simple score (e.g., normalized momentum + trend
   consistency).
4. **No period-over-period comparison**: no "this period vs previous
   period" delta for moving averages or price.
5. **No Pydantic schemas**: analytics domain models are dataclasses, not
   Pydantic — need API schemas for serialization.
6. **No frontend metrics UI**: no stats cards, trend arrows, or sparklines
   on card detail.

## Architecture

### Backend Changes

#### 1. Extend analytics indicators

Add two new pure functions to `src/analytics/indicators.py`:

- `compute_performance_score(prices, period_days) -> PerformanceScore`:
  normalized composite of momentum RoC, trend consistency (count of
  positive vs negative daily deltas), and proximity to ATH. Returns a
  score 0-100 and a label ("strong"/"moderate"/"weak"/"declining").

- `compute_period_comparison(prices, period_days) -> PeriodComparison`:
  compare current period vs immediately preceding period of same length.
  Returns current_avg, previous_avg, delta, delta_pct.

Add new domain dataclasses: `PerformanceScore`, `PeriodComparison`.

#### 2. Extend `CardAnalytics` computation

Update `compute_card_analytics()` to accept an optional `period_days`
parameter. When set, filter the price list to that window before
computing volatility and momentum. Always compute extremes over the full
dataset. Add `performance` and `period_comparison` fields to
`CardAnalytics`.

#### 3. API endpoint

Add `GET /collection/{entry_id}/metrics?period=30d&currency=BRL` to
`src/api/routers/collection.py`.

Response schema `CardMetricsResponse`:
```python
class MovingAverageSchema(BaseModel):
    period: int
    value: float

class PriceExtremesSchema(BaseModel):
    ath_price: float
    ath_date: date
    atl_price: float
    atl_date: date

class VolatilitySchema(BaseModel):
    period_days: int
    std_dev: float
    coefficient_of_variation: float

class MomentumSchema(BaseModel):
    period_days: int
    rate_of_change: float
    trend_direction: str  # "up" | "down" | "flat"

class PerformanceScoreSchema(BaseModel):
    score: int  # 0-100
    label: str  # "strong" | "moderate" | "weak" | "declining"
    period_days: int

class PeriodComparisonSchema(BaseModel):
    current_avg: float
    previous_avg: float
    delta: float
    delta_pct: float
    period_days: int

class CardMetricsResponse(BaseModel):
    entry_id: int
    card_id: int
    period: str
    currency: str
    moving_averages: list[MovingAverageSchema]
    extremes: PriceExtremesSchema | None
    volatility: VolatilitySchema | None
    momentum: MomentumSchema | None
    performance: PerformanceScoreSchema | None
    period_comparison: PeriodComparisonSchema | None
    data_points: int
```

The endpoint resolves entry -> card -> source_cards -> price series,
runs `compute_card_analytics()`, and serializes via the schemas above.
Currency conversion applies to all price values.

#### 4. No database changes

All metrics are computed at query time from existing `price_observations`
data. No new tables, columns, or migrations.

### Frontend Changes

#### 1. MetricsPanel component

New `frontend/src/components/MetricsPanel.tsx`. Renders a grid of stat
cards below or beside the price chart on the collection card detail page.

Cards:
- **Trend**: arrow icon (up/down/flat) + rate of change percentage,
  colored green/red/gray.
- **Moving Averages**: MA-7 and MA-30 values side by side.
- **ATH / ATL**: all-time high and low with dates.
- **Volatility**: coefficient of variation with a visual bar indicator
  (low/medium/high).
- **Performance**: score 0-100 with label badge ("strong" green,
  "moderate" amber, "weak" gray, "declining" red).
- **Period Comparison**: current vs previous period avg with delta arrow.

Uses the same period as the PriceChart (shared via prop or URL param).

#### 2. API client function

Add `fetchCardMetrics(entryId, period, currency)` to
`frontend/src/api/collection.ts`.

#### 3. Integration in CollectionCardDetail

Add `MetricsPanel` below the PriceChart in the right column. Pass the
current period and currency. Show skeleton loading state while metrics
load.

#### 4. i18n keys

Add keys for metric labels, trend directions, performance labels,
period comparison text in both EN and PT-BR.

## Acceptance Criteria

1. `GET /collection/{entry_id}/metrics?period=30d` returns all computed
   metrics for the card's price history scoped to the requested period
2. Moving averages (7d, 30d), ATH/ATL, volatility, momentum, performance
   score, and period comparison are all present in the response when
   sufficient data exists
3. Metrics gracefully degrade: fields are null when data is insufficient
   (e.g., <2 data points for volatility)
4. Currency conversion applies to all price-denominated metrics
5. Frontend shows metrics as stat cards on collection card detail page
6. Metrics update when the user changes the period selector
7. Trend direction shown with colored arrow (green up, red down, gray flat)
8. Performance score shown as 0-100 with color-coded label
9. All new backend code has unit tests
10. All new frontend components have tests
11. i18n keys added for EN and PT-BR

## Constraints

- Depends on F33 shipping first (period-based queries, PriceChangeSummary)
- No new database tables or columns — all computed at query time
- Analytics functions remain pure (no DB imports)
- Decimal arithmetic in backend; float in API schemas (Pydantic)
- Reuse existing KPI card styling from Dashboard where applicable

## Tasks

| Task | File | Wave | Description |
|------|------|------|-------------|
| T01 | F34-T01.md | 1 | Backend: new analytics functions + domain models |
| T02 | F34-T02.md | 1 | Backend: metrics API endpoint + Pydantic schemas |
| T03 | F34-T03.md | 2 | Frontend: MetricsPanel component + API client |
| T04 | F34-T04.md | 2 | Frontend: CollectionCardDetail integration + i18n |
| T05 | F34-T05.md | 3 | Tests: backend + frontend comprehensive coverage |

## Waves

- **Wave 1** (2 tasks, parallel): T01 (analytics functions), T02 (API
  endpoint + schemas). T02 depends on T01's domain models but both can
  be developed in parallel if T01 lands first within the wave.
- **Wave 2** (2 tasks, parallel): T03 (MetricsPanel component),
  T04 (page integration + i18n)
- **Wave 3** (1 task): T05 (tests for all new code)

## File Inventory

### New Files
- `src/api/schemas/metrics.py` — Pydantic schemas (T02)
- `frontend/src/components/MetricsPanel.tsx` — metrics display (T03)
- `frontend/src/api/metrics.ts` — API client (T03)
- `tests/unit/analytics/test_performance.py` — new function tests (T05)
- `tests/unit/api/test_metrics_endpoint.py` — endpoint tests (T05)
- `frontend/tests/components/MetricsPanel.test.tsx` — component tests (T05)

### Modified Files
- `src/analytics/indicators.py` — add performance_score, period_comparison (T01)
- `src/domain/models.py` — add PerformanceScore, PeriodComparison dataclasses (T01)
- `src/api/routers/collection.py` — add metrics endpoint (T02)
- `frontend/src/pages/CollectionCardDetail.tsx` — integrate MetricsPanel (T04)
- `frontend/src/i18n/locales/en.json` — metric i18n keys (T04)
- `frontend/src/i18n/locales/pt-BR.json` — metric i18n keys (T04)

### No Cross-Wave File Conflicts
- Wave 1: `indicators.py` (T01), `collection.py` router (T02) — no overlap
- Wave 2: `MetricsPanel.tsx` (T03), `CollectionCardDetail.tsx` (T04) — no overlap
- Wave 3: test files only (T05)
