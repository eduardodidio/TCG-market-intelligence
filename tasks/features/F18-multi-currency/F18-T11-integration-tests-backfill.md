# F18-T11: Integration Tests + Historical Rate Backfill Script

- **Wave:** 4
- **Status:** done
- **Depends on:** F18-T06, F18-T08, F18-T10
- **Description:**
  Two deliverables in this task:

  **1. End-to-end integration tests** covering the full currency flow:

  - Seed exchange rates in test DB.
  - Create price observations in BRL.
  - Call API endpoints with `?currency=USD`.
  - Verify converted values match expected: `brl_value / rate`.
  - Verify `?currency=BRL` returns original values unchanged.
  - Verify missing rate fallback behavior.
  - Verify price history conversion uses per-date rates.
  - Test the CLI `update-exchange-rate --backfill-days 7` with mocked
    BCB responses.

  **2. One-time backfill script** (`scripts/backfill_exchange_rates.py`):

  - Fetches historical PTAX rates for the last 365 days.
  - Uses `fetch_rate_range()` from the BCB client.
  - Stores all rates via `bulk_upsert_rates()`.
  - Can be run manually after initial deployment.
  - Includes progress logging.

- **Acceptance Criteria:**
  - [ ] Integration test: USD conversion returns correct values
  - [ ] Integration test: BRL returns unchanged values
  - [ ] Integration test: missing rate falls back to closest previous
  - [ ] Integration test: empty rate table + USD returns null prices
  - [ ] Integration test: CLI backfill populates rates
  - [ ] Backfill script fetches 365 days from BCB
  - [ ] Backfill script is idempotent (safe to re-run)
  - [ ] Backend test count increases by 15+ tests
  - [ ] Coverage stays >= 70%

- **Files to touch:**
  - `tests/integration/test_currency_e2e.py` (new)
  - `tests/integration/cli/test_cli_exchange_rate.py` (new)
  - `scripts/backfill_exchange_rates.py` (new)
