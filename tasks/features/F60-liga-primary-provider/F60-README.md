# F60 — LigaMagic Primary Provider Migration

**Status:** done
**Created:** 2026-08-25
**Priority:** P0 (foundational platform change)

## Summary

Migrate the entire platform to use LigaMagic as the primary price source.
MYP becomes a manual fallback only (button click). Includes a Liga-aware
scan orchestrator, initial full-collection sweep CLI, price history cleanup,
admin link monitor dashboard, scheduled Liga scans, and price priority
reordering.

## User Story

As a collector, I want card prices sourced from LigaMagic (the most relevant
Brazilian MTG marketplace) so that my collection value reflects real market
prices. MYP remains available as a manual fallback button.

## Acceptance Criteria

1. Liga scans work end-to-end: CLI, API, SSE progress, scheduled
2. `get_latest_prices_batch` prioritizes Liga > Manual > MYP on same-date ties
3. Admin page shows link/price coverage status for the collection
4. `tcg liga-sweep` runs a full collection sweep with resume support
5. `tcg db-clear-prices --source jsonld_snapshot --confirm` clears old MYP prices
6. Card detail shows Liga as primary refresh, MYP as secondary fallback
7. Scheduled scans: daily partial (50 cards) + weekly full
8. Price history charts show Liga observations correctly

## Architecture Decisions

- Liga concurrency MUST be 1 (single Playwright browser, ~5.5s/card)
- Liga delay between cards: 5s default (configurable)
- Liga scans save as `source="liga"`, `external_id="liga_{card_id}"`
- Scan orchestrator refactored to accept any CardSourceProvider (not hardcoded MYP)
- New `ScanType.LIGA_FULL` and `ScanType.LIGA_PARTIAL` enum values
- New `get_cards_for_liga_scan()` repo method (queries by card_id + name, not MYP source_cards)
- MYP scan path preserved unchanged for backward compat

## Waves

### Wave 0 — Backend Foundation (parallel tasks)
- T01: Refactor scan orchestrator for generic provider
- T02: Liga scan repo method + price priority update
- T03: Clear prices CLI command

### Wave 1 — Liga Scan Integration (parallel tasks)
- T04: Liga scan orchestrator (end-to-end)
- T05: Liga sweep CLI command
- T06: Scan API + CLI provider flag

### Wave 2 — Frontend (parallel tasks)
- T07: Admin link monitor page
- T08: Card detail Liga/MYP button priority
- T09: i18n keys for new UI

### Wave 3 — Scheduling
- T10: Scheduled Liga scans (APScheduler integration)

## Task Count: 10
## Wave Count: 4
