# F18-T08: Add Currency Parameter to Price-Returning Endpoints

- **Wave:** 2
- **Status:** done
- **Depends on:** F18-T05
- **Description:**
  Add an optional `currency` query parameter (default `"BRL"`, accepts
  `"USD"`) to all API endpoints that return price data. When `currency=USD`,
  use the `CurrencyConverter` service to convert all price fields before
  returning them.

  Endpoints to modify:

  1. **`GET /cards`** — convert `latest_price` in each CardSummary.
  2. **`GET /cards/{id}`** — convert `latest_price` in CardDetail.
  3. **`GET /cards/{id}/history`** — convert `median_price`, `tcg_price`,
     `last_sold_price` in each PriceObservation. Use batch conversion
     keyed by `observed_at` date.
  4. **`GET /collection`** — convert `latest_price` in each CollectionCard.
  5. **`GET /collection/summary`** — convert `total_value`.
  6. **`GET /collection/{id}`** — convert `latest_price` and all entries
     in `price_history`.
  7. **`GET /market/stats`** — convert `avg_price`.
  8. **`GET /market/movers`** — convert `price_start` and `price_end`.

  Implementation approach:
  - Create a FastAPI dependency `get_currency_converter()` that returns
    a `CurrencyConverter` instance.
  - Add a `currency: str = Query(default="BRL")` parameter with
    validation (must be "BRL" or "USD").
  - Add a `currency` field to response schemas that do not already have
    one: `CardSummary`, `CardDetail`, `CollectionCard`,
    `CollectionSummary`, `MarketStats`, `MoverEntry`.
  - Existing `PriceObservation.currency` field is already present.

- **Acceptance Criteria:**
  - [ ] All 8 endpoints accept `?currency=USD`
  - [ ] Default `?currency=BRL` returns unchanged values (no regression)
  - [ ] Invalid currency value returns 422
  - [ ] Response includes `currency` field reflecting the requested currency
  - [ ] Price history conversion uses per-observation-date rates
  - [ ] Movers conversion uses the rate for each period's date
  - [ ] Tests for BRL (default) and USD on each endpoint
  - [ ] No existing tests broken

- **Files to touch:**
  - `src/api/routers/cards.py`
  - `src/api/routers/collection.py`
  - `src/api/routers/market.py`
  - `src/api/schemas/cards.py`
  - `src/api/schemas/collection.py`
  - `src/api/schemas/market.py`
  - `src/api/deps.py`
  - `tests/unit/api/test_cards_currency.py` (new)
  - `tests/unit/api/test_collection_currency.py` (new)
  - `tests/unit/api/test_market_currency.py` (new)
