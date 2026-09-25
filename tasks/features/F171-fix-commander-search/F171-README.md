# F171 — Fix commander card search (deck builder returns no results)

**Status:** planned
**Branch:** homol
**Complexity:** Small bugfix (3 tasks, 1 wave)

## Problem

Commander search in the DeckBuildWizard returns zero results even though cards
exist in the database. The root cause is a data enrichment gap combined with
an overly strict query.

### Root Cause Chain

1. **Price collector creates bare cards.** `Repository.upsert_card()` (line 368)
   creates `CardRow` with only `game`, `name_en`, `name_pt`, `set_code`,
   `collector_number`. Fields `type_line`, `rarity`, `color_identity`,
   `mana_cost`, `image_uri` are all `NULL`.

2. **Catalog seeder never enriches existing cards.** `seeder._process_card_batch()`
   uses `on_conflict_do_nothing` (line 73). If a card already exists from step 1,
   the Scryfall metadata is silently discarded.

3. **Commander search requires non-NULL type_line.** `get_commander_candidates()`
   filters `CardRow.type_line.isnot(None)` AND `CardRow.type_line.contains("Legendary")`
   AND `CardRow.type_line.contains("Creature")`. Cards from step 1 are excluded.

4. **The `_excluded_by_legality` subquery is correctly implemented** as a soft
   filter (cards without legality rows pass through). This is NOT a contributing
   factor.

### Affected Scope

- `src/catalog/seeder.py` — needs `on_conflict_do_update` for metadata fields
- `src/database/repository.py` — `upsert_card` should propagate Scryfall
  metadata when available
- `src/decks/builder.py` — `get_commander_candidates` and `_query_candidates`
  could be more resilient, but the real fix is in the data layer
- Tests in `tests/unit/decks/test_commander_search.py`

## Task List

| Task | Title | Wave | Depends |
|------|-------|------|---------|
| T01 | Catalog seeder: enrich existing cards on conflict | W1 | -- |
| T02 | CLI backfill command for cards missing Scryfall metadata | W1 | -- |
| T03 | Tests for enrichment + commander search with pre-existing cards | W1 | -- |

## Wave Plan

### Wave 1 (all parallel)

All three tasks are independent and can run simultaneously:

- **T01** changes the seeder to use `on_conflict_do_update` so re-running
  `catalog seed` fills in missing metadata on existing cards.
- **T02** adds a lightweight CLI command (`catalog enrich`) that queries cards
  with `type_line IS NULL` and updates them from existing Scryfall-seeded data
  or triggers a re-seed. This gives operators a quick fix without a full re-seed.
- **T03** adds test coverage for the specific scenario: card created by price
  collector (bare), then catalog seed runs, then commander search finds it.

## Acceptance Criteria

1. After running `catalog seed`, cards previously created by price collection
   have their `type_line`, `rarity`, `color_identity`, `mana_cost`, and
   `image_uri` filled from Scryfall data.
2. Commander search returns results for cards that were enriched.
3. A CLI command exists to audit/fix cards with missing metadata.
4. Existing tests pass; new tests cover the enrichment path.
5. No new dependencies introduced.
