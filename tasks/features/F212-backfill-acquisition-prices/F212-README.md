# F212 — Backfill Acquisition Prices

**Status:** planned
**Created:** 2026-11-19
**Type:** data migration + feature

## Summary

Populate `acquisition_price` for the entire collection (currently 0/1180 entries
have prices) using three data sources:
1. DeckCheck Binder CSV (USD, 77.5% coverage, 915/1180 matches)
2. Nerdz Cards purchase HTMLs (BRL, 24 files)
3. Liga Magic purchase HTML (BRL, 1 file)

## Wave Plan

| Wave | Tasks | Parallelism |
|------|-------|-------------|
| 0 | T01, T02 | Parallel (independent sources, no shared code) |
| 1 | T03 | Sequential (depends on T01+T02 results) |

## Tasks

| ID | Title | Files | Est. |
|----|-------|-------|------|
| T01 | CLI: backfill-prices from DeckCheck CSV | new CLI command + parser | M |
| T02 | Run Nerdz+Liga HTML import via existing pipeline | no code — use existing UI/API | S |
| T03 | Verify & report final coverage | query + report | S |

## Data Sources

### DeckCheck CSV (`docs/deckcheck-binder-colecao-mtg-20261028.csv`)
- 941 rows (header + 941 data)
- Columns: `Card Scryfall ID`, `Name`, `Set Code`, `Collector Number`,
  `Rarity`, `Finish`, `Quantity`, **`Purchase Price`**, `Current Price`, etc.
- Currency: USD (decimal dot format, e.g. `0.19`, `12.50`)
- Match key: `(Name, Set Code, Collector Number)` -> `user_collection` entries
- Coverage: 915/1180 entries (77.5%)

### Nerdz+Liga HTMLs (`docs/comprasEmLojas/`)
- 24 Nerdz order HTMLs + 1 Liga order HTML
- BRL prices, already supported by purchase_parser.py + purchase_matcher.py
- UI: `ImportPurchasesPage` (drag-drop)

## Acceptance Criteria

- [ ] 900+ collection entries have acquisition_price after backfill
- [ ] USD prices correctly converted to BRL
- [ ] No existing acquisition_prices overwritten (skip if already set)
- [ ] Coverage report shows final numbers
