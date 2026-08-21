# F18-T01: Exchange Rate DB Model + Migration

- **Wave:** 0
- **Status:** done
- **Depends on:** none
- **Description:**
  Add an `ExchangeRateRow` SQLAlchemy model to `src/database/models.py`
  representing the `exchange_rates` table. The table stores daily exchange
  rates with columns: `id` (PK), `rate_date` (DATE, UNIQUE), `from_currency`
  (VARCHAR(3), default 'USD'), `to_currency` (VARCHAR(3), default 'BRL'),
  `rate` (NUMERIC(12,6)), `source` (VARCHAR(50), default 'bcb_ptax'),
  `created_at` (DATETIME). The rate semantics are "1 USD = X BRL".

  Since the project uses SQLAlchemy `create_all` (no Alembic), the new
  table is created automatically. Ensure `Base.metadata` includes the
  new model and that it is imported in the right places.

- **Acceptance Criteria:**
  - [ ] `ExchangeRateRow` class exists in `src/database/models.py`
  - [ ] Table has unique constraint on `rate_date` (one rate per day)
  - [ ] Index on `rate_date` for fast lookups
  - [ ] `from_currency` defaults to 'USD', `to_currency` defaults to 'BRL'
  - [ ] `rate` column uses NUMERIC(12,6) for precision
  - [ ] Unit test confirms model can be instantiated and table created

- **Files to touch:**
  - `src/database/models.py`
  - `tests/unit/database/test_models.py` (new or extend)
