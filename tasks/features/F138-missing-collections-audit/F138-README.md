# F138 — Missing Collections Audit

**Status:** planned
**Created:** 2026-09-18
**Slug:** missing-collections-audit

## Summary

CLI command `catalog missing` that compares Scryfall catalog sets against
price-scanned sets in the DB, reports coverage gaps, and outputs a
ready-to-use scan list for `catalog-scan-batch.sh`.

## Motivation

We have 994 sets seeded from Scryfall but only 129 have any Liga price data.
The user needs a quick way to see which sets (especially those in their
collection) still need price scanning, and generate a batch script to fill
the gaps.

## Waves

### Wave 0 (1 task — CLI command)

| Task | Description | Parallel? |
|------|-------------|-----------|
| T01  | `catalog missing` CLI command + batch output | Independent |

## Acceptance Criteria

1. `python -m src.cli.main catalog missing` prints a report with:
   - Collection sets without any prices
   - Partially scanned sets (< 50% priced, prioritized by collection membership)
   - Total coverage stats
2. `--format script` outputs shell commands ready to paste into catalog-scan-batch.sh
3. `--min-cards N` filters to sets with at least N cards (default: 50)
4. `--collection-only` limits report to sets present in user collection
5. Tests cover all output modes
