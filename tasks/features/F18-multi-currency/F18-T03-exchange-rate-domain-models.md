# F18-T03: Exchange Rate Domain Models

- **Wave:** 0
- **Status:** done
- **Depends on:** none
- **Description:**
  Add domain dataclasses to `src/domain/models.py` for exchange rate data:

  1. `ExchangeRate` — represents a single daily exchange rate:
     - `rate_date: date`
     - `from_currency: str = "USD"`
     - `to_currency: str = "BRL"`
     - `rate: Decimal` (1 USD = X BRL)
     - `source: str = "bcb_ptax"`

  2. `Currency` — str enum with values `BRL` and `USD`.

  3. `ConvertedPrice` — a price value with its currency and the rate used:
     - `value: Decimal | None`
     - `currency: str`
     - `exchange_rate: Decimal | None` (None when currency is BRL)
     - `rate_date: date | None`

- **Acceptance Criteria:**
  - [ ] `ExchangeRate` dataclass in `src/domain/models.py`
  - [ ] `Currency` enum with BRL and USD values
  - [ ] `ConvertedPrice` dataclass for explicit conversion results
  - [ ] Unit tests for dataclass instantiation
  - [ ] No circular imports introduced

- **Files to touch:**
  - `src/domain/models.py`
  - `tests/unit/domain/test_models.py` (extend)
