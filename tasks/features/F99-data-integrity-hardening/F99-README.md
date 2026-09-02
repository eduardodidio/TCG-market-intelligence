# F99 -- Data Integrity Hardening

**Status:** planned

## Summary

Add foreign key constraints, composite indexes, atomic transactions, and
cascade behavior to the SQLite database. Fix the N+1 query in orphan
linking and add exchange rate fallback logic.

## Problem

The database has no FK constraints -- all `card_id` references are plain
integers with no referential integrity enforcement. Collection deletion
does not cascade to DeckCardRow or other dependent tables. The sync
pipeline lacks atomic transactions (partial failures leave inconsistent
state). The exchange rate converter returns `None` silently when no rate
exists for the exact date. The `link_orphan_source_cards` method issues
one query per orphan (N+1 pattern).

## Goals

1. Clean orphan records that would violate FK constraints
2. Add FK constraints on all `card_id` references
3. Enable `PRAGMA foreign_keys=ON` per connection via SQLAlchemy events
4. Add composite indexes on hot query paths
5. Fix N+1 in `link_orphan_source_cards` (single JOIN update)
6. Wrap sync pipeline in atomic transaction with rollback on failure
7. Exchange rate fallback to nearest available date (within 7 days)
8. Collection deletion cascade: SET NULL on DeckCardRow.card_id

## Waves

### Wave 0 -- Orphan Cleanup + Indexes (safe, no schema changes)
| Task | Description |
|------|-------------|
| T01  | Orphan record cleanup (pre-FK constraint preparation) |
| T02  | Composite indexes on hot query paths |

### Wave 1 -- FK Constraints + Engine Config (depends on Wave 0)
| Task | Description |
|------|-------------|
| T03  | PRAGMA foreign_keys=ON in engine config |
| T04  | FK constraints migration on all card_id columns |
| T05  | Fix N+1 in link_orphan_source_cards |

### Wave 2 -- Transaction Safety + Rate Fallback (depends on Wave 1)
| Task | Description |
|------|-------------|
| T06  | Atomic transaction wrapper for sync pipeline |
| T07  | Exchange rate fallback to nearest historical rate |

### Wave 3 -- Cascade Behavior + Tests (depends on Wave 2)
| Task | Description |
|------|-------------|
| T08  | Collection deletion cascade (SET NULL on deck_cards.card_id) |
| T09  | Integration tests for FK constraints and cascade behavior |

## Key Architectural Decisions

- SQLite requires `PRAGMA foreign_keys=ON` per connection (not global).
  This is set via a SQLAlchemy `event.listen(engine, "connect", ...)` hook.
- Orphan records MUST be cleaned BEFORE adding FK constraints, otherwise
  the migration will fail with constraint violations.
- The FK migration uses SQLite's table-rebuild strategy (create new table
  with FKs, copy data, drop old, rename) since SQLite does not support
  `ALTER TABLE ADD CONSTRAINT`.
- DeckCardRow.card_id on collection entry deletion should be SET NULL
  (not CASCADE delete) -- the deck card still exists in the deck, it just
  loses its link to the canonical card.
- The sync pipeline transaction wraps steps 3b through 3g (upsert card,
  upsert source_card, insert observations, link entry, resolve errors)
  but NOT the external API calls (search, fetch).

## Files Likely Modified

- `src/database/repository.py` (engine config, link_orphan, delete methods)
- `src/database/models.py` (FK constraints, new indexes)
- `src/database/cleanup.py` (orphan cleanup additions)
- `src/collectors/sync_collection.py` (atomic transaction wrapper)
- `src/services/currency.py` (rate fallback logic)
- `tests/` (new integration tests)
