# T02 — Fix Missing oracle_text Column (1 test)

**Status:** planned
**Wave:** 0
**Estimate:** S

## User Story

As a developer, I want the card catalog column test to pass so the schema
expectation matches the actual model.

## Problem

`tests/unit/database/test_card_catalog_columns.py::test_cards_table_has_all_expected_columns`
expects an `oracle_text` column in `CardRow` but the model doesn't have it.

## Dev Notes

### Decision: Add oracle_text to CardRow

The deck evaluator (`src/decks/synergy.py`) already uses `oracle_text` via
`pat.search(oracle_text)`. Currently it receives this from API/mock data.
Adding `oracle_text` to `CardRow` is the correct fix because:
- Scryfall bulk data includes `oracle_text` for every card
- The seeder (`src/catalog/seeder.py`) can populate it
- The evaluator can then read it from DB directly

### Implementation
1. Add `oracle_text = Column(Text, nullable=True)` to `CardRow` in
   `src/database/models.py`
2. Add Alembic migration or ensure `create_all()` picks it up (SQLite
   auto-creates via `metadata.create_all`)
3. Update `src/catalog/seeder.py` to map Scryfall's `oracle_text` field
4. Verify test passes

### Files to Modify
- `src/database/models.py` — add column
- `src/catalog/seeder.py` — map field during seed

## Testing

- Run: `pytest tests/unit/database/test_card_catalog_columns.py --override-ini="addopts=" -q`
- Expected: 1 test passes
