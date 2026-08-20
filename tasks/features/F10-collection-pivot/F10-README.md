# F10 -- Collection-Centric Pivot

**Status:** in-review

## Summary

Pivot the platform from a generic market scanner to a personal collection tracker with market intelligence. The feature implements a sync pipeline that searches MYP Cards for each card in the user's imported collection, fetches price history, and stores it in the database. Before any destructive operations, a dry-run match report shows coverage. After sync, existing frontend pages (Dashboard, Cards, CardDetail) gracefully handle the new collection-centric data.

## What F10 Delivers

1. **Dry-run match report** (Saruman condition #1) -- CLI command that searches MYP for each collection card and reports matched/unmatched/ambiguous without writing to the DB.
2. **DB backup + cleanup** (Saruman condition #2) -- SQLite `.backup()` before deleting cards/source_cards/price_observations not in the user's collection. Set code normalization (uppercase to lowercase) across all tables.
3. **Collection sync pipeline** -- Async orchestrator that, for each matched collection card, creates/updates CardRow + SourceCardRow, fetches 365 days of price history, stores observations, and links user_collection entries.
4. **CLI command** -- `sync-collection` with `--dry-run`, `--limit`, `--concurrency` flags.
5. **API endpoint** -- `POST /api/v1/collection/sync` (async job, auth-required).
6. **Frontend adjustments** (Saruman condition #3) -- Dashboard shows collection-aware stats, Cards page shows collection cards by default, empty states make sense post-cleanup, CardDetail uses Scryfall HD images.
7. **Documentation** -- PRD, Mermaid diagrams (architecture + journey), README update, ADR for the collection-centric pivot decision.

## Wave Structure

### Wave 0 -- Dry-run Match Report (Saruman #1)
| Task | Description | Estimate |
|------|-------------|----------|
| F10-T01 | MYP search adapter (search by name, parse results) | M |
| F10-T02 | Collection matcher (match collection entries to MYP search results) | M |
| F10-T03 | Dry-run match report CLI command | S |

### Wave 1 -- DB Backup + Cleanup + Normalization (Saruman #2)
| Task | Description | Estimate |
|------|-------------|----------|
| F10-T04 | DB backup utility + cleanup of non-collection data | M |
| F10-T05 | Set code normalization (uppercase to lowercase) | S |

### Wave 2 -- Core Sync Pipeline
| Task | Description | Estimate |
|------|-------------|----------|
| F10-T06 | Collection sync orchestrator (search, match, fetch, store, link) | L |

### Wave 3 -- CLI + API
| Task | Description | Estimate |
|------|-------------|----------|
| F10-T07 | CLI sync-collection command | S |
| F10-T08 | API POST /collection/sync endpoint | S |

### Wave 4 -- Frontend Adjustments (Saruman #3)
| Task | Description | Estimate |
|------|-------------|----------|
| F10-T09 | Dashboard collection-aware stats + Cards page defaults | M |
| F10-T10 | CardDetail Scryfall HD image + empty state polish | S |

### Wave 5 -- Documentation + Integration Tests
| Task | Description | Estimate |
|------|-------------|----------|
| F10-T11 | PRD, Mermaid diagrams, README update, ADR | M |
| F10-T12 | Integration tests for sync pipeline end-to-end | M |

## Dependencies

- **F01-F08** infrastructure (provider, parsers, repository, API, frontend) -- all shipped.
- **POC code** from current session (collection importer, API router, MyCollection page) -- working, will be improved, not rewritten.
- MYP search API availability (`/produto/search?marca=magic&term={query}`).

## Risks

| Risk | Mitigation |
|------|------------|
| MYP search API rate limiting / blocks | Reuse existing Semaphore(3) + 2s delay; ~35-40 min for 548 cards is acceptable |
| Low match rate (cards not found on MYP) | Dry-run report (Wave 0) surfaces coverage before any destructive changes |
| Set code mismatch between collection CSV and MYP SKU | Normalize both to lowercase; match by set_code + collector_number first, then fall back to name fuzzy match |
| DB cleanup deletes data user still wants | SQLite `.backup()` before any deletion; user reviews dry-run report first |
| MYP search returns ambiguous results (multiple matches) | Match by set_code + collector_number from SKU; log ambiguous matches for review |

## Estimates

- Total tasks: 12
- Estimated effort: ~2-3 developer sessions
- Sync runtime: ~35-40 minutes for 548 cards (rate-limited)
