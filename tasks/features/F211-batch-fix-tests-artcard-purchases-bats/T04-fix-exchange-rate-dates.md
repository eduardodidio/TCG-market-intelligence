# T04 — Fix Exchange Rate Date Logic Tests (4 tests)

**Status:** planned
**Wave:** 0
**Estimate:** S

## User Story

As a developer, I want date-sensitive tests to use relative dates so they
don't rot as calendar time advances.

## Problem

4 tests fail because they use hardcoded dates (e.g. `2026-08-20`) that were
"future" when written but are now in the past:

- `tests/integration/database/test_repository_exchange_rates.py::TestGetClosestRate::test_ignores_future_dates`
- `tests/integration/test_currency_e2e.py::TestMissingRateFallback::test_empty_rate_table_usd_returns_null`
- `tests/integration/cli/test_cli_exchange_rate.py::TestUpdateExchangeRateCLI::test_backfill_is_idempotent`
- `tests/unit/services/test_currency.py::TestConvert::test_returns_none_when_no_rate`

## Dev Notes

### Fix Strategy
Replace hardcoded "future" dates with `date.today() + timedelta(days=N)`:

```python
# Before (rots)
future_date = date(2026, 8, 20)

# After (always future)
future_date = date.today() + timedelta(days=30)
```

Also check if "past" dates used in the same tests are still correctly in the
past relative to the test's "today".

### Files to Modify
- `tests/integration/database/test_repository_exchange_rates.py`
- `tests/integration/test_currency_e2e.py`
- `tests/integration/cli/test_cli_exchange_rate.py`
- `tests/unit/services/test_currency.py`

## Testing

- Run: `pytest tests/integration/database/test_repository_exchange_rates.py::TestGetClosestRate::test_ignores_future_dates tests/integration/test_currency_e2e.py::TestMissingRateFallback::test_empty_rate_table_usd_returns_null tests/integration/cli/test_cli_exchange_rate.py::TestUpdateExchangeRateCLI::test_backfill_is_idempotent tests/unit/services/test_currency.py::TestConvert::test_returns_none_when_no_rate --override-ini="addopts=" -q`
- Expected: 4 tests pass
