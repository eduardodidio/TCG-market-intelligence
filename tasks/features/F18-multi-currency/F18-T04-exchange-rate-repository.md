# F18-T04: Exchange Rate Repository Methods

- **Wave:** 1
- **Status:** done
- **Depends on:** F18-T01, F18-T03
- **Description:**
  Add repository methods to `src/database/repository.py` for exchange rate
  CRUD operations:

  1. `upsert_exchange_rate(rate: ExchangeRate)` — insert or update a rate
     for a given date. Uses INSERT ON CONFLICT (rate_date) DO UPDATE.
  2. `get_exchange_rate(rate_date: date) -> ExchangeRateRow | None` —
     exact date lookup.
  3. `get_closest_rate(target_date: date) -> ExchangeRateRow | None` —
     returns the rate for `target_date`, or the most recent rate before it.
     This is the primary lookup method for conversion (handles weekends,
     holidays, and missing data).
  4. `get_latest_rate() -> ExchangeRateRow | None` — returns the most
     recent rate in the table.
  5. `get_rate_history(days: int = 30) -> list[ExchangeRateRow]` — returns
     rates for the last N days, ordered by date descending.
  6. `bulk_upsert_rates(rates: list[ExchangeRate])` — batch insert for
     historical backfill.

- **Acceptance Criteria:**
  - [ ] All 6 methods implemented in Repository class
  - [ ] `get_closest_rate` falls back to most recent earlier rate
  - [ ] `get_closest_rate` returns None when table is empty
  - [ ] `upsert_exchange_rate` is idempotent (same date updates rate)
  - [ ] Integration tests with in-memory SQLite
  - [ ] Tests cover edge cases: empty table, future date, exact match

- **Files to touch:**
  - `src/database/repository.py`
  - `tests/integration/database/test_repository_exchange_rates.py` (new)
