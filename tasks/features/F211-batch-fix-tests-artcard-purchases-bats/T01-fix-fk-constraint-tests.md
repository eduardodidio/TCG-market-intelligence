# T01 — Fix FK Constraint Test Failures (41 tests)

**Status:** planned
**Wave:** 0
**Estimate:** S

## User Story

As a developer, I want all marketplace/deck/collection repository tests to pass
so that CI is green and we can trust the test suite.

## Problem

41 tests fail with `sqlite3.IntegrityError: FOREIGN KEY constraint failed`:

- `tests/unit/database/test_repository_marketplace.py` (37 tests):
  SharedCollectionCRUD, TradeInterestCRUD, TradeAgreementCRUD,
  GetSharedCollectionByCode, ListSharedCollections, GetUserTrades.
  All insert into `shared_collections`/`trade_interests`/`trade_agreements`
  referencing `user_id=1` without creating the user row first.

- `tests/unit/database/test_repository_decks.py` (2 tests):
  `test_card_fields_stored`, `test_links_card` — insert into `deck_cards`
  with `card_id=42` referencing non-existent card.

- `tests/unit/database/test_repository_collection.py` (2 tests):
  `TestCollectionSummaryPricedCount` — insert `source_cards` with
  `card_id=100` referencing non-existent card.

## Dev Notes

### Root Cause
FK constraints are ON (enforced since F99). Test fixtures create child rows
without first creating the required parent rows (users, cards).

### Fix Strategy
1. In each failing test file's `repo` fixture (or a shared conftest helper),
   insert the prerequisite parent rows before the test body runs:
   - For marketplace tests: create a `UserRow` with `id=1` (and any other
     user IDs used by the tests).
   - For deck tests: create a `CardRow` with `id=42` (or whatever `card_id`
     the test references).
   - For collection tests: create a `CardRow` with `id=100`.

2. Use raw SQL or model inserts via the repo's session to keep it minimal.
   A shared helper like `_seed_user(session, user_id)` and
   `_seed_card(session, card_id)` would reduce duplication.

3. Do NOT disable FK constraints — they exist for a reason.

### Files to Modify
- `tests/unit/database/test_repository_marketplace.py` — update `repo` fixture
- `tests/unit/database/test_repository_decks.py` — update fixture
- `tests/unit/database/test_repository_collection.py` — update fixture

## Testing

- Run: `pytest tests/unit/database/test_repository_marketplace.py tests/unit/database/test_repository_decks.py tests/unit/database/test_repository_collection.py --override-ini="addopts=" -q`
- Expected: 41 previously-failing tests now pass, 0 regressions
