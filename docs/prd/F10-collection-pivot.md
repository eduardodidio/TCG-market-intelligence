# PRD: F10 - Collection-Centric Pivot

**Status:** Delivered
**Date:** 2026-08-19
**Author:** Eduardo Rutkoski Didio
**ADR:** [0004-collection-centric-pivot](../adr/0004-collection-centric-pivot.md)

## Problem

TCG Market Intelligence was built as a generic market scanner that discovers
and tracks every Magic card available on MYP Cards. After expanding to 240+
cards across 8 sets (F08), two problems became clear:

1. **Signal-to-noise ratio.** The user owns ~548 unique cards. Tracking
   thousands of cards the user does not own creates noise in the dashboard,
   wastes collection bandwidth, and produces market movers dominated by
   irrelevant cards.

2. **No collection awareness.** The platform has no concept of "my cards."
   The user cannot import their collection, see which cards they own, or
   get a portfolio valuation. The dashboard shows aggregate market stats
   that have no personal relevance.

The user wants to pivot from "scan the entire market" to "track my
collection and show me intelligence about the cards I own."

## User Personas

- **Solo collector / investor** -- owns a personal Magic collection tracked
  in a CSV export. Wants to see current prices, historical trends, and
  portfolio value for the cards they actually own. Does not care about cards
  they do not own.

## Goals

1. Import the user's collection from a CSV file into a `user_collection`
   table
2. Search MYP Cards for each collection card and match by SKU or name
3. Provide a dry-run match report before any destructive operations
4. Clean up the database to remove cards not in the collection
5. Sync price history for all matched collection cards
6. Show collection-aware stats on the Dashboard (card count, total value,
   coverage percentage)
7. Display Scryfall HD card images on the Card Detail page
8. Normalize set codes to lowercase across the entire pipeline

## Functional Requirements

| ID    | Requirement |
|-------|-------------|
| FR-01 | CSV import parses the user's collection export and inserts rows into `user_collection` with set_code, collector_number, name_en, name_pt, quantity, quality, language, rarity, color, and extras |
| FR-02 | MYP search adapter calls `/produto/search?marca=magic&term={name}` and returns structured `MypSearchResult` objects |
| FR-03 | Collection matcher scores search results against collection entries using a priority chain: SKU exact > name+set > name only > ambiguous > unmatched |
| FR-04 | `match-report` CLI command runs a dry-run match against MYP for all collection entries and prints a summary with match/ambiguous/unmatched counts and confidence levels |
| FR-05 | `match-report --output report.json` writes detailed per-card results to a JSON file |
| FR-06 | `db-backup` CLI command creates a timestamped SQLite backup using `sqlite3.backup()` |
| FR-07 | `db-cleanup` CLI command removes cards, source_cards, and price_observations not linked to the user's collection; creates an automatic backup first |
| FR-08 | `db-cleanup --dry-run` shows what would be deleted without actually deleting |
| FR-09 | `sync-collection` CLI command orchestrates the full pipeline: search MYP, match, fetch card details, fetch price history, upsert card + source_card, insert observations, link collection entry |
| FR-10 | `sync-collection --dry-run` runs the pipeline without writing to the database |
| FR-11 | `sync-collection --force` re-syncs entries that already have a `card_id` link |
| FR-12 | `POST /api/v1/collection/sync` triggers a background sync job (auth-required) |
| FR-13 | `GET /api/v1/collection` lists collection cards with latest prices and Scryfall image URLs |
| FR-14 | `GET /api/v1/collection/summary` returns collection KPIs: unique cards, total copies, estimated value, linked count, sets count |
| FR-15 | Dashboard shows collection KPIs (cards, copies, estimated value, coverage %) |
| FR-16 | Card Detail page displays Scryfall HD card images via the redirect API |
| FR-17 | All set codes are normalized to lowercase throughout import, matching, and storage |

## Non-Functional Requirements

| ID     | Requirement |
|--------|-------------|
| NFR-01 | Sync pipeline respects MYP rate limits: `asyncio.Semaphore(3)` with configurable delay (default 1s) |
| NFR-02 | Sync is resumable: entries with existing `card_id` are skipped by default |
| NFR-03 | Errors during sync are logged per-card and do not abort the entire run |
| NFR-04 | DB backup uses SQLite's native `backup()` API for consistency |
| NFR-05 | Cleanup requires an existing collection (refuses to run on empty `user_collection`) |
| NFR-06 | Match report is read-only -- no database writes occur |
| NFR-07 | Scryfall images use the redirect endpoint (no API key required, no rate limit concerns for browser requests) |
| NFR-08 | No new Python dependencies introduced |

## Out of Scope

- Multi-user support (single hardcoded user_id)
- Image caching or local storage of card images
- Fuzzy/phonetic name matching (exact match only)
- Automatic CSV re-import on file change
- Collection edit/delete from the UI
- Trade/sell tracking
- Price alerts or notifications

## Data Model Changes

New table added to `src/database/models.py`:

```
user_collection
  id, user_id, card_id (FK to cards), set_code, collector_number,
  name_en, name_pt, set_name_en, quantity, quality, language,
  rarity, color, extras, created_at
```

New domain models in `src/domain/models.py`:

- `MypSearchResult` -- structured search API response
- `SyncSummary`, `SyncResult`, `SyncError` -- sync pipeline tracking

New modules:

- `src/collection/importer.py` -- CSV import logic
- `src/collection/matcher.py` -- pure matching logic (no DB/network)
- `src/collectors/match_report.py` -- dry-run match report orchestrator
- `src/collectors/sync_collection.py` -- sync pipeline orchestrator
- `src/database/backup.py` -- SQLite backup utility
- `src/database/cleanup.py` -- non-collection data cleanup

## Success Metrics

| Metric | Target |
|--------|--------|
| Match rate (SKU exact + name+set) | > 80% of collection cards |
| Sync completion rate | > 95% of matched cards successfully synced |
| Sync runtime | < 45 minutes for 548 cards (rate-limited) |
| Dashboard load time | < 2 seconds with collection data |

## Acceptance Criteria

1. **AC1:** `match-report` prints match/ambiguous/unmatched counts for the
   full collection
2. **AC2:** `db-backup` creates a timestamped `.db` backup file
3. **AC3:** `db-cleanup --dry-run` shows deletion counts without modifying
   the database
4. **AC4:** `sync-collection` populates cards + price_observations for
   matched collection entries
5. **AC5:** Dashboard shows collection KPIs (cards, copies, value, coverage)
6. **AC6:** Card Detail page displays Scryfall card images
7. **AC7:** All set codes in the database are lowercase after normalization
8. **AC8:** All existing tests continue to pass
9. **AC9:** Documentation complete (PRD, ADR, diagrams, README)
