# PRD: F08 - Data Enrichment

**Status:** Planned
**Date:** 2026-08-19
**Author:** Eduardo Rutkoski Didio
**Gandalf Decision:** D-20260819-001

## Problem

After the F07 frontend dashboard shipped, manual testing revealed three data
quality issues that undermine the usefulness of the dashboard:

1. **Double-encoded UTF-8 card names.** Names like "Contramagica" display as
   garbled text ("Contram\u00c3\u00a1gica") because the raw bytes were
   decoded with the wrong charset (likely latin-1 instead of UTF-8) before
   being stored. Every card name with accented characters is affected.

2. **Flat price charts and 0% movers.** The Dashboard fetches movers with
   `period=7d`, but price observations are weekly, so every card shows 0%
   change. Additionally, many DMR cards have genuinely stable median prices,
   making charts appear as flat lines even over longer periods.

3. **Insufficient data variety.** Only 30 cards from a single set (DMR) have
   been collected. With so few cards and one set, the dashboard lacks
   meaningful data diversity for market analysis.

## User Personas

- **Data Analyst / Collector** -- needs accurate card names (searchable in
  PT/EN), meaningful price movement signals, and data from multiple sets to
  compare trends across the market.

## Goals

1. Fix encoding so all card names display correctly in the API and frontend
2. Ensure the Dashboard movers section shows meaningful price changes
3. Expand the collected dataset to multiple popular sets for richer analysis

## Functional Requirements

| ID    | Requirement |
|-------|-------------|
| FR-01 | Parser produces correctly-encoded UTF-8 strings for all card names |
| FR-02 | Existing DB records with broken encoding are migrated to correct UTF-8 |
| FR-03 | Dashboard default movers period changes from 7d to 30d |
| FR-04 | At least 5 additional popular Magic sets are collected via backfill |
| FR-05 | Collection expansion uses existing backfill infrastructure (resume-safe) |

## Non-Functional Requirements

| ID     | Requirement |
|--------|-------------|
| NFR-01 | Encoding fix must be idempotent -- running migration twice is safe |
| NFR-02 | Existing tests continue to pass after encoding changes |
| NFR-03 | Collection expansion respects existing rate limiting and concurrency |
| NFR-04 | No new dependencies introduced for the encoding fix |

## Out of Scope

- Changing the movers algorithm or adding new price series (tcg_price) to
  movers calculation -- that is a separate feature
- Adding card images from Scryfall
- Portfolio features
- Deployment configuration

## Acceptance Criteria

1. **AC1:** `curl localhost:8000/api/v1/cards?limit=5` returns correctly
   encoded Portuguese names (e.g., "Contramagica" not "Contram...gica")
2. **AC2:** Dashboard movers section shows non-zero price changes for at
   least some cards
3. **AC3:** Database contains cards from at least 5 sets beyond DMR
4. **AC4:** All existing backend and frontend tests pass
5. **AC5:** Documentation updated (diagrams, README)
