# F86 Database Price & Card Reset (Keep Collection)

**Status:** done

## Description

Full database reset that wipes price data and removes non-collection cards,
while preserving collection entries, user data, decks, credits, and all
other user-facing state. The goal is to start fresh with a clean scan after
previous data became stale or was collected with the wrong strategy.

### What gets deleted

| Table               | Action                                                       |
|---------------------|--------------------------------------------------------------|
| `price_observations`| **Truncate** -- delete ALL rows, every source                |
| `scan_runs`         | **Truncate** -- delete ALL rows (audit trail reset)          |
| `portfolio_snapshots`| **Truncate** -- derived from prices, now invalid            |
| `cards`             | **Selective** -- delete cards with no `user_collection` row  |
| `source_cards`      | **Selective** -- delete source_cards whose `card_id` is NULL or points to a deleted card |
| `card_legalities`   | **Selective** -- delete rows whose `card_id` is in deleted cards set |
| `legality_history`  | **Selective** -- delete rows whose `card_id` is in deleted cards set |
| `collection_errors` | **Truncate** -- stale error records, safe to clear           |

### What is preserved (sacred)

| Table                 | Reason                         |
|-----------------------|--------------------------------|
| `user_collection`     | Core user data                 |
| `users`               | Auth / identity                |
| `credit_balances`     | Token economy                  |
| `credit_transactions` | Audit trail                    |
| `decks`               | User-created decks             |
| `deck_cards`          | Deck contents                  |
| `exchange_rates`      | Independent of card data       |
| `scheduled_scans`     | User config                    |
| `shared_collections`  | User config                    |
| `trade_interests`     | User activity                  |
| `trade_agreements`    | User activity                  |

### Post-reset state

- `user_collection.card_id` remains set for entries whose card survived
  (the card is in the collection, so it was not deleted).
- Source cards linked to surviving cards are also preserved -- only
  orphan/non-collection source_cards are removed.
- After reset, user runs `liga-sweep` or `scan` to rebuild prices.

## Wave Breakdown

### Wave 0 (single wave -- all in one task)

| Task | Description |
|------|-------------|
| T01  | `db-reset` service function + CLI command + tests |

This is a single-wave, single-task feature. The logic is a composition of
patterns already established in `cleanup.py` and `reset-prices`, with the
addition of cascading deletes for legality and portfolio data.

## Acceptance Criteria

1. CLI command `db-reset` with `--confirm` flag (dry-run by default)
2. Auto-backup before any destructive operation (existing `backup_database`)
3. Dry-run shows exact row counts per table that would be deleted
4. Refuses to run if `user_collection` is empty (existing safety pattern)
5. All price_observations, scan_runs, portfolio_snapshots, collection_errors deleted
6. Cards not referenced by any collection entry are deleted
7. Source_cards and legalities for deleted cards are cascade-deleted
8. Collection entries, users, decks, credits, exchange rates untouched
9. VACUUM runs after deletion to reclaim disk space
10. Unit tests cover: dry-run counts, actual deletion, empty-collection guard, backup creation
