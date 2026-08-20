# PRD: F10 - Collection-Centric Pivot

**Status:** Shipped
**Date:** 2026-08-19
**Author:** Eduardo Rutkoski Didio
**Gandalf Decision:** D-20260819-003

## Problem

After shipping F01-F08, the platform collected price data across multiple
Magic sets via generic backfill. However, the user only owns ~548 unique cards
across ~134 sets. The dashboard displayed aggregate market statistics for
hundreds of cards the user does not own, making the data noisy and impersonal.

Only 3 of 548 collection cards matched existing DB data (0.5% match rate),
proving the generic backfill strategy collected data with minimal value to
the actual user.

## User Personas

### Collector (Primary)
A single user who owns a Magic: The Gathering collection and wants to:
- See their collection's total market value
- Track price trends for cards they own
- Know which cards have price data coverage on MYP

## Functional Requirements

### FR1: Dry-Run Match Report
- CLI command `match-report` searches MYP for each collection card
- Reports matched/ambiguous/unmatched counts with percentages
- No database writes (read-only operation)
- Supports `--limit`, `--output` (JSON), `--concurrency` flags

### FR2: Database Backup & Cleanup
- `db-backup` creates timestamped SQLite backup via `sqlite3.backup()`
- `db-cleanup` removes cards, source_cards, price_observations not in
  the user's collection
- Safety: refuses to run with empty collection, auto-backup before delete
- Supports `--dry-run` and `--no-backup` flags

### FR3: Set Code Normalization
- All set codes normalized to lowercase across DB, parsers, and importers
- `parse_sku()` returns lowercase set codes
- Migration script for existing DB data

### FR4: Collection Sync Pipeline
- Async orchestrator: search -> match -> fetch card page -> fetch history -> store -> link
- Resumable: `skip_matched=True` skips already-linked entries
- Rate-limited with `asyncio.Semaphore(concurrency)` (default 3)
- Error isolation: individual card failures don't abort the sync

### FR5: CLI Command
- `sync-collection` with `--dry-run`, `--limit`, `--concurrency`,
  `--history-days`, `--force`, `--delay` flags
- Prints formatted summary after completion

### FR6: API Endpoint
- `POST /api/v1/collection/sync` triggers async background job
- Requires API key auth (same pattern as backfill/update)
- Request body: `limit`, `history_days`, `force`

### FR7: Frontend Adjustments
- Dashboard shows collection KPIs (cards, copies, value, coverage %)
- Cards page works with collection-scoped data post-cleanup
- CardDetail shows Scryfall HD card images
- Empty states updated for collection-centric messaging

## Non-Functional Requirements

- Sync runtime: ~35-55 minutes for 548 cards (rate-limited to avoid MYP blocks)
- All set codes lowercase (no case-insensitive comparisons needed)
- Backend test coverage >= 70% (project threshold)
- No new external dependencies

## Out of Scope

- Multi-user support (single-user application)
- Image caching or local storage (Scryfall CDN-fetched)
- Automatic re-sync scheduling (future feature, post-F10)
- Portfolio tracking (cost basis, P&L)

## Success Metrics

- Match report coverage rate > 50% of collection cards
- Sync completion rate > 95% of matched cards
- Dashboard loads without errors with collection-scoped data
- All existing tests pass (no regressions)
