# T05 — Fix Deck Evaluation MagicMock Oracle Text (3 tests)

**Status:** planned
**Wave:** 0
**Estimate:** S

## User Story

As a developer, I want deck evaluation endpoint tests to provide proper
string fixtures instead of MagicMock objects so regex matching works.

## Problem

3 tests in `tests/unit/api/test_deck_endpoints.py::TestEvaluateDeck` fail:
- `test_evaluate_returns_valid_data`
- `test_evaluate_with_format_legality`
- `test_evaluate_with_budget`

Error: `TypeError: expected string or bytes-like object, got 'MagicMock'`
at `src/decks/synergy.py:170` where `pat.search(oracle_text)` is called.

## Dev Notes

### Root Cause
Test fixtures mock deck card data but leave `oracle_text` as a default
MagicMock instead of providing a string value.

### Fix Strategy
1. Find the mock/fixture that creates card data for the evaluate endpoint
2. Set `oracle_text` to a realistic string value (e.g. `"Draw two cards."`)
3. Ensure all card objects passed to the evaluator have string oracle_text

### Files to Modify
- `tests/unit/api/test_deck_endpoints.py` — fix mock data

## Testing

- Run: `pytest tests/unit/api/test_deck_endpoints.py::TestEvaluateDeck --override-ini="addopts=" -q`
- Expected: 3 tests pass
