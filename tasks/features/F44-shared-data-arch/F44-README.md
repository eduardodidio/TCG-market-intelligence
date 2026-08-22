# F44 — Arquitetura Compartilhada de Dados (Shared Data Architecture)

**Status:** shipped
**Created:** 2026-08-21
**Dependencies:** F33 (Price History), F34 (History Metrics) -- both planned

## Summary

Consolidate market data access into a shared core layer that all consumer
features (Ticker, Landing, Market Page, Top Decks, My Collection, Ban
Engine) can use. Today each feature independently queries `Repository`,
calls analytics functions, and converts currencies inside its own router.
F44 introduces a `MarketDataService` facade, a pre-computation layer for
expensive aggregates, and an event-driven refresh mechanism triggered by
scan completion.

## Problem Statement

### Current Pain Points

1. **Duplicated data-assembly logic**: `market.py`, `collection.py`,
   `cards.py` all independently fetch prices, resolve source cards,
   convert currencies, and build response objects. The "get latest price
   for a card" pattern is copy-pasted across 4+ routers.

2. **No pre-computation**: `get_movers()` iterates every card in the DB
   on every request, running 2 queries per card (earliest + latest price).
   `get_market_stats()` does a full table scan of `price_observations`.
   These will not scale as the dataset grows.

3. **No event-driven refresh**: after a scan completes, aggregates are
   stale until the next request recalculates them. There is no mechanism
   to refresh materialized data when new observations land.

4. **No shared response shapes**: each router defines its own price/card
   schemas. `MoverEntry`, `CollectionCard`, `CardSummary` all represent
   "a card with a price" but share no base type.

5. **CurrencyConverter created per-request**: `get_currency_converter_dep`
   creates a new `Repository` + `CurrencyConverter` on every call, losing
   the in-memory rate cache between requests.

### What This Feature Does NOT Do

- Does NOT implement any consumer feature (Ticker, Landing, etc.)
- Does NOT add new database tables for pre-computation in this phase
  (uses in-memory caching with TTL instead)
- Does NOT change the scan orchestrator itself (only hooks into its
  completion signal)

## Architecture

### Layer Diagram

```
Routers (market, collection, cards, future features)
    |
    v
MarketDataService  <-- single facade
    |
    +-- PriceLookup       (latest prices, price series, batch lookups)
    +-- AnalyticsComputer  (wraps src/analytics/indicators.py)
    +-- AggregateCache     (daily summary, top movers, trending scores)
    |
    v
Repository + CurrencyConverter  (existing, unchanged)
```

### Component Details

#### 1. MarketDataService (`src/services/market_data.py`)

A stateful service class instantiated once per application lifecycle
(FastAPI lifespan). Holds references to Repository, CurrencyConverter,
and AggregateCache. Provides high-level methods:

- `get_card_market_data(card_id, currency, period)` -- latest price,
  price series, analytics metrics (when F34 ships), all currency-converted.
- `get_top_movers(period, limit, currency)` -- delegates to cache.
- `get_market_summary(currency)` -- delegates to cache.
- `get_cards_with_prices(card_ids, currency)` -- batch lookup with
  currency conversion. Replaces the pattern duplicated across routers.
- `invalidate(card_ids)` -- called after scan completion to mark
  specific card data as stale.

#### 2. AggregateCache (`src/services/aggregate_cache.py`)

In-memory cache with TTL-based expiry. Stores pre-computed results:

- **Daily market summary**: total cards, total observations, avg price,
  date range. TTL: 1 hour.
- **Top movers** (per period): gainers + losers lists. TTL: 30 minutes.
- **Latest price map**: card_id -> latest price observation. TTL: 15
  minutes (or invalidated by scan completion).

Implementation: simple dict with `(key, computed_at)` tuples. No
external dependencies (no Redis). Thread-safe via `threading.Lock`.

Cache keys are `(method_name, *args)` tuples. `invalidate(card_ids)`
clears entries that reference any of the given card IDs plus clears
the summary/movers caches entirely (they are cheap to recompute once,
expensive to compute on every request).

#### 3. Shared Schemas (`src/api/schemas/market_data.py`)

Common response shapes that consumer features import:

```python
class CardPriceInfo(BaseModel):
    """Base price info attached to any card representation."""
    card_id: int
    latest_price: Decimal | None
    currency: str
    price_date: date | None

class MarketCardSummary(BaseModel):
    """Card summary with market data -- shared across features."""
    card_id: int
    name_en: str
    name_pt: str | None
    set_code: str | None
    collector_number: str | None
    image_url: str | None
    price: CardPriceInfo | None

class DailySummary(BaseModel):
    """Pre-computed daily market summary."""
    total_cards: int
    total_observations: int
    avg_price: Decimal | None
    date_range_start: date | None
    date_range_end: date | None
    currency: str
    computed_at: datetime
```

Existing router-specific schemas (e.g., `CollectionCard`) can embed
or extend `CardPriceInfo` rather than duplicating price fields.

#### 4. Scan Completion Hook (`src/services/scan_hooks.py`)

A simple callback registry. The scan orchestrator (`run_scan()`) calls
`on_scan_complete(scan_run)` after finishing. Registered hooks:

- `AggregateCache.invalidate(affected_card_ids)` -- clears stale cache.
- Future hooks: WebSocket push, notification, etc.

The hook is injected into `run_scan()` as an optional callback parameter
(no tight coupling). Default is no-op when no hooks registered.

#### 5. Service Dependency (`src/api/deps.py`)

Add a `get_market_data_service()` FastAPI dependency that returns the
singleton `MarketDataService`. Uses `@lru_cache` or app-state pattern
to ensure single instance across requests.

### Refactoring Strategy

Phase 1 (this feature): create the service layer and wire it into the
`market.py` router only. Verify it works identically to the current
implementation. Other routers continue using Repository directly.

Phase 2 (future features F35-F40): migrate remaining routers to use
`MarketDataService` as they are built or modified.

This avoids a risky big-bang refactor while establishing the shared
pattern immediately.

## Acceptance Criteria

1. `MarketDataService` exists with methods for card market data, top
   movers, market summary, and batch price lookup
2. `AggregateCache` provides TTL-based in-memory caching with
   thread-safe invalidation
3. `market.py` router refactored to use `MarketDataService` instead of
   calling `Repository` directly -- API behavior unchanged
4. Scan completion triggers cache invalidation via hook callback
5. Shared `CardPriceInfo` and `MarketCardSummary` schemas exist in
   `src/api/schemas/market_data.py`
6. `get_market_data_service()` FastAPI dependency provides singleton
7. All existing tests still pass (no behavioral changes)
8. New code has comprehensive unit tests (service, cache, hooks)
9. No new database tables or columns
10. No new external dependencies

## Constraints

- In-memory cache only (no Redis, no SQLite cache tables)
- Thread-safe (FastAPI runs with thread pool for sync endpoints)
- Cache invalidation is best-effort (stale data is acceptable for
  short TTL windows)
- Decimal arithmetic preserved throughout (no float conversion in
  service layer)
- Existing router behavior must not change (refactor, not rewrite)

## Tasks

| Task | File | Wave | Description |
|------|------|------|-------------|
| T01 | F44-T01.md | 0 | AggregateCache: TTL-based in-memory cache |
| T02 | F44-T02.md | 1 | Shared API schemas (CardPriceInfo, MarketCardSummary) |
| T03 | F44-T03.md | 1 | MarketDataService facade |
| T04 | F44-T04.md | 2 | Scan completion hook + wiring |
| T05 | F44-T05.md | 2 | Refactor market.py router to use MarketDataService |
| T06 | F44-T06.md | 3 | FastAPI dependency + singleton lifecycle |
| T07 | F44-T07.md | 4 | Tests: service, cache, hooks, refactored router |

## Waves

- **Wave 0** (1 task): T01 -- AggregateCache is a standalone utility
  with no dependencies on other new code. Can be built and tested in
  isolation.
- **Wave 1** (2 tasks, parallel): T02 (shared schemas) and T03
  (MarketDataService). T03 uses T01's cache. T02 and T03 have no
  mutual dependency.
- **Wave 2** (2 tasks, parallel): T04 (scan hooks) and T05 (market
  router refactor). T04 wires cache invalidation into scan_orchestrator.
  T05 refactors market.py to use the service from T03.
- **Wave 3** (1 task): T06 -- FastAPI dependency wiring. Depends on
  T03 (service) and T05 (refactored router) being in place.
- **Wave 4** (1 task): T07 -- comprehensive test suite covering all
  new code and verifying no behavioral regression.

## File Inventory

### New Files
- `src/services/aggregate_cache.py` (T01)
- `src/api/schemas/market_data.py` (T02)
- `src/services/market_data.py` (T03)
- `src/services/scan_hooks.py` (T04)
- `tests/unit/services/test_aggregate_cache.py` (T07)
- `tests/unit/services/test_market_data.py` (T07)
- `tests/unit/services/test_scan_hooks.py` (T07)
- `tests/integration/test_market_router_service.py` (T07)

### Modified Files
- `src/collectors/scan.py` -- add optional `on_complete` callback (T04)
- `src/api/routers/market.py` -- use MarketDataService (T05)
- `src/api/deps.py` -- add `get_market_data_service()` (T06)

### Untouched (Phase 2 migration targets)
- `src/api/routers/collection.py`
- `src/api/routers/cards.py`
- `src/api/routers/scans.py`
- `src/api/routers/decks.py`

## File Conflicts

- T04 and T05 both depend on T03 outputs but modify different files
  (`scan.py` vs `market.py`) -- no conflict.
- T06 modifies `deps.py` which is not touched by any other task.
- No cross-wave file conflicts exist.
