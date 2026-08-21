# F18-T05: Currency Conversion Service

- **Wave:** 1
- **Status:** done
- **Depends on:** F18-T03, F18-T04
- **Description:**
  Create `src/services/currency.py` with a `CurrencyConverter` class that
  encapsulates all conversion logic:

  1. `__init__(self, repo: Repository)` — takes a repository for rate
     lookups.
  2. `convert(value: Decimal, from_date: date, to_currency: str) -> Decimal | None`
     — converts a BRL value to the target currency using the exchange rate
     for `from_date`. Returns the value unchanged if `to_currency == "BRL"`.
     Returns None if no rate is available.
  3. `convert_price_observation(obs: PriceObservationRow, to_currency: str) -> PriceObservationRow`
     — returns a copy of the observation with all price fields converted.
     Sets the `currency` field to the target currency.
  4. `convert_batch(values: list[tuple[Decimal, date]], to_currency: str) -> list[Decimal | None]`
     — batch conversion that pre-fetches all needed rates in one query
     to avoid N+1.
  5. `get_rate_for_date(target_date: date) -> Decimal | None` — public
     method that wraps `repo.get_closest_rate()`.

  The service caches rates in memory during a single request lifecycle
  (dict keyed by date) to avoid repeated DB lookups when converting a
  price history series.

- **Acceptance Criteria:**
  - [ ] BRL-to-USD conversion: `brl_value / rate`
  - [ ] BRL-to-BRL returns value unchanged (no DB lookup)
  - [ ] Returns None when no rate exists and target is USD
  - [ ] In-memory cache avoids repeated DB queries for same date
  - [ ] `convert_batch` makes at most one DB query
  - [ ] Unit tests with mocked repository (10+ test cases)
  - [ ] Edge cases: None values, zero prices, Decimal precision

- **Files to touch:**
  - `src/services/__init__.py` (new if needed)
  - `src/services/currency.py` (new)
  - `tests/unit/services/test_currency.py` (new)
