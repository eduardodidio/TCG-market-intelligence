# F36 — Cards em Alta e em Baixa (Trending Cards Engine)

**Status:** shipped
**Created:** 2026-08-21
**Dependencies:** F34 (History Metrics — must ship first)

## Summary

Build a trending cards engine that identifies cards with significant,
sustained price movements. Goes beyond the existing "movers" feature
(`GET /market/movers`) which only compares first vs last price in a
window. The trending engine adds a composite score that combines
percentage change, consistency of direction, observation density, and
minimum-price filters to eliminate false trending signals.

## User Story

As a collector or trader, I want to see which cards are genuinely
trending up or down over configurable periods, with false positives
filtered out (sub-$1 noise, single-observation spikes, inconsistent
zig-zag movement), so I can spot real market trends quickly.

## Current State Analysis

### What Already Exists

1. **Market movers** (`src/api/routers/market.py`, `Repository.get_movers()`):
   returns top gainers/losers by simple `(latest - earliest) / earliest`
   percentage. No consistency check, no minimum observation count, no
   minimum price filter. Scans all cards via N+1 queries (slow).

2. **Analytics indicators** (`src/analytics/indicators.py`): pure functions
   for moving averages, price extremes, volatility, and momentum (rate of
   change + trend direction). `compute_momentum()` gives RoC and
   "up"/"down"/"flat" for a single card.

3. **F34 (planned)**: adds `compute_performance_score()` (composite 0-100
   with momentum, consistency, ATH proximity) and
   `compute_period_comparison()` (current vs previous period avg).

4. **Price data**: `price_observations` table with
   `(source, external_id, observed_at, median_price, ...)`. Cards link
   via `source_cards.card_id -> cards.id`.

5. **Frontend**: `MarketMovers.tsx` page with `MoversTable` component,
   period selector (7d/30d/90d), limit selector. Uses `MoverEntry` schema
   with `card_id, name_en, name_pt, set_code, price_start, price_end,
   change_pct, currency`.

### Gaps to Fill

1. **No composite trending score**: movers uses raw % change only. Needs
   consistency (consecutive direction days), observation density, and
   time-decay weighting.
2. **No false-trending filters**: no minimum observation count (a card
   with 1 observation "gaining" 0% passes), no minimum price threshold
   (sub-R$1 cards with 100% noise-driven swings dominate), no consistency
   check.
3. **No pre-computation / caching**: `get_movers()` does N+1 queries over
   all cards on every request. Trending needs batch computation with
   caching to keep response times acceptable.
4. **No dedicated trending API**: movers endpoint returns gainers+losers
   but not a ranked trending list with composite scores.
5. **No frontend trending component**: no card tiles with change arrows,
   trending badges, or score indicators beyond the basic `MoversTable`.
6. **No image URLs on movers**: existing `MoverEntry` lacks
   `collector_number` and `image_url`, so movers show as text-only tables.

## Architecture

### Backend Changes

#### 1. Trending score engine (pure functions)

New file `src/analytics/trending.py` with pure functions (no DB imports):

```python
@dataclass
class TrendingScore:
    card_id: int
    change_pct: Decimal        # raw % change over period
    change_abs: Decimal         # absolute price change
    consistency: Decimal        # 0-1, fraction of days moving same direction
    observation_count: int      # number of data points in window
    observation_density: Decimal # obs_count / period_days (0-1)
    composite_score: Decimal    # weighted final score (0-100)
    direction: str              # "up" | "down"
    price_start: Decimal
    price_end: Decimal

def compute_trending_score(
    prices: list[tuple[date, Decimal]],
    period_days: int,
) -> TrendingScore | None:
    """Compute composite trending score for a single card's price series."""

def rank_trending(
    scores: list[TrendingScore],
    direction: str,  # "up" | "down"
    min_observations: int = 3,
    min_price: Decimal = Decimal("1.00"),
    min_consistency: Decimal = Decimal("0.5"),
    limit: int = 20,
) -> list[TrendingScore]:
    """Filter and rank trending cards by composite score."""
```

Composite score formula:
- **change_weight** (40%): normalized |change_pct| clamped to [0, 100]
- **consistency_weight** (30%): consistency * 100
- **density_weight** (20%): observation_density * 100
- **recency_weight** (10%): bonus if the most recent observation is
  within the last 2 days

Anti-false-trending filters in `rank_trending()`:
- `min_observations >= 3`: cards with fewer than 3 data points are excluded
- `min_price >= R$1.00`: start price must be above threshold to avoid
  penny-card noise
- `min_consistency >= 0.5`: at least 50% of daily deltas must go in the
  same direction as the overall change

#### 2. Trending service (orchestration + caching)

New file `src/services/trending.py`:

```python
class TrendingService:
    def __init__(self, repo: Repository):
        self._repo = repo
        self._cache: dict[str, tuple[datetime, TrendingResponse]] = {}
        self._cache_ttl = timedelta(minutes=30)

    def get_trending(
        self,
        direction: str,
        period_days: int,
        limit: int,
        converter: CurrencyConverter,
        currency: str,
    ) -> TrendingResponse:
        """Return cached or freshly computed trending cards."""
```

The service:
1. Checks in-memory cache keyed by `f"{direction}:{period_days}"`.
2. On cache miss, loads all cards with source_cards in a single batch
   query (no N+1).
3. For each card, fetches price series for the period in a batch.
4. Runs `compute_trending_score()` on each card's price series.
5. Runs `rank_trending()` with anti-false-trending filters.
6. Caches result with 30-min TTL.

#### 3. Repository: batch price query

Add `Repository.get_trending_price_data(period_days)` that returns
`dict[int, list[tuple[date, Decimal]]]` mapping card_id to price series.
Single query using a JOIN between `cards`, `source_cards`, and
`price_observations` with date filter. This replaces the N+1 pattern
in `get_movers()`.

#### 4. API endpoints

Add to existing `src/api/routers/market.py`:

```
GET /market/trending/gainers?period=30d&limit=20&currency=BRL
GET /market/trending/losers?period=30d&limit=20&currency=BRL
```

Response schema `TrendingResponse`:

```python
class TrendingCardEntry(BaseModel):
    card_id: int
    name_en: str
    name_pt: str | None
    set_code: str | None
    collector_number: str | None
    image_url: str | None
    price_start: float
    price_end: float
    change_pct: float
    change_abs: float
    consistency: float     # 0-1
    composite_score: float # 0-100
    observation_count: int
    currency: str

class TrendingResponse(BaseModel):
    cards: list[TrendingCardEntry]
    period: str
    direction: str  # "up" | "down"
    computed_at: datetime
    cached: bool
```

#### 5. Pydantic schemas

New file `src/api/schemas/trending.py` with the schemas above.

### Frontend Changes

#### 1. TrendingCard component

New `frontend/src/components/TrendingCard.tsx`: a card tile showing:
- Card image (small thumbnail from Scryfall)
- Card name (language-aware via `useCardName`)
- Set code badge
- Price change arrow (green up / red down) with % and absolute change
- Composite score bar (thin progress bar, green gradient)
- Consistency indicator (dot pattern: filled dots = consistent days)

#### 2. TrendingSection component

New `frontend/src/components/TrendingSection.tsx`: a horizontal
scrollable row of `TrendingCard` tiles with a section header
("Trending Up" / "Trending Down"), period selector, and "View All"
link. Reusable for embedding on Dashboard or a dedicated page.

#### 3. Trending page

New `frontend/src/pages/Trending.tsx` at route `/market/trending`:
- Full-page view with gainers and losers sections
- Period selector (7d / 30d / 90d)
- Limit control
- Loading skeletons, error states, empty states
- Currency-aware via `useCurrency`

#### 4. API client + types

New `frontend/src/api/trending.ts` with `fetchTrending(direction,
params)`. New types in `frontend/src/types/api.ts`.

#### 5. Navigation + i18n

Add "Trending" nav link to sidebar/header. Add i18n keys for trending
labels, direction names, score labels in EN and PT-BR.

### No Database Schema Changes

All computation is from existing `price_observations` + `cards` +
`source_cards` tables. Caching is in-memory (process-level dict with TTL).

## Acceptance Criteria

1. `GET /market/trending/gainers?period=30d` returns cards ranked by
   composite trending score, not just raw % change
2. `GET /market/trending/losers?period=30d` returns cards trending down
3. Cards with fewer than 3 observations in the period are excluded
4. Cards with start price below R$1.00 are excluded
5. Cards with consistency below 50% are excluded
6. Composite score weights: change 40%, consistency 30%, density 20%,
   recency 10%
7. Results are cached for 30 minutes per (direction, period) combination
8. Batch query for price data (no N+1 queries)
9. Currency conversion works for all price fields
10. Frontend shows trending cards with image, price change arrow, and
    composite score indicator
11. Period selector (7d/30d/90d) updates results
12. Trending page accessible at `/market/trending`
13. i18n keys added for EN and PT-BR
14. All new backend code has unit tests
15. All new frontend components have tests

## Constraints

- Depends on F34 shipping first (uses F34's domain patterns, but the
  trending score engine is self-contained and does NOT call F34 functions)
- No new database tables or columns
- Analytics/trending pure functions must not import from database layer
- In-memory cache only (no Redis/external cache)
- Decimal arithmetic in backend; float in API schemas
- Minimum 3 observations to qualify as trending
- Minimum R$1.00 start price to avoid penny-card noise

## Tasks

| Task | File | Wave | Description |
|------|------|------|-------------|
| T01 | F36-T01.md | 1 | Backend: trending score engine (pure functions) |
| T02 | F36-T02.md | 1 | Backend: batch price query in Repository |
| T03 | F36-T03.md | 2 | Backend: trending service + API endpoints + schemas |
| T04 | F36-T04.md | 3 | Frontend: TrendingCard + TrendingSection components |
| T05 | F36-T05.md | 3 | Frontend: Trending page + routing + i18n |
| T06 | F36-T06.md | 4 | Tests: backend + frontend comprehensive coverage |

## Waves

- **Wave 1** (2 tasks, parallel): T01 (pure scoring functions), T02
  (batch repository query). No dependencies between them.
- **Wave 2** (1 task): T03 (trending service + API). Depends on both
  T01 and T02.
- **Wave 3** (2 tasks, parallel): T04 (components), T05 (page + routing).
  Both depend on T03 for the API contract but can be built in parallel
  since they touch different files.
- **Wave 4** (1 task): T06 (tests for all new code).

## File Inventory

### New Files
- `src/analytics/trending.py` — pure trending score functions (T01)
- `src/services/trending.py` — service with caching + orchestration (T03)
- `src/api/schemas/trending.py` — Pydantic schemas (T03)
- `frontend/src/components/TrendingCard.tsx` — card tile component (T04)
- `frontend/src/components/TrendingSection.tsx` — scrollable section (T04)
- `frontend/src/pages/Trending.tsx` — full trending page (T05)
- `frontend/src/api/trending.ts` — API client functions (T04)
- `tests/unit/analytics/test_trending.py` — pure function tests (T06)
- `tests/unit/services/test_trending_service.py` — service tests (T06)
- `tests/unit/api/test_trending_endpoint.py` — endpoint tests (T06)
- `frontend/tests/components/TrendingCard.test.tsx` — component tests (T06)
- `frontend/tests/components/TrendingSection.test.tsx` — component tests (T06)
- `frontend/tests/pages/Trending.test.tsx` — page tests (T06)

### Modified Files
- `src/database/repository.py` — add `get_trending_price_data()` (T02)
- `src/api/routers/market.py` — add trending endpoints (T03)
- `frontend/src/App.tsx` — add `/market/trending` route (T05)
- `frontend/src/components/Layout.tsx` or nav component — add nav link (T05)
- `frontend/src/types/api.ts` — add trending types (T04)
- `frontend/src/i18n/locales/en.json` — trending i18n keys (T05)
- `frontend/src/i18n/locales/pt-BR.json` — trending i18n keys (T05)

### No Cross-Wave File Conflicts
- Wave 1: `trending.py` analytics (T01), `repository.py` (T02) — no overlap
- Wave 2: `market.py` router + `trending.py` service + schemas (T03) — standalone
- Wave 3: `TrendingCard.tsx` + `TrendingSection.tsx` (T04), `Trending.tsx`
  page + `App.tsx` (T05) — no overlap
- Wave 4: test files only (T06)
