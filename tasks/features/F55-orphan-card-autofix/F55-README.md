# F55 -- Orphan Card Auto-Fix

**Status:** shipped

## Problem

Two related issues prevent collection entries from getting price data:

1. **Matcher returns "ambiguous" instead of best-effort.** When MYP search
   returns multiple printings of the same card (e.g., "Abrade" in HOU, 2XM,
   LTR) and no SKU or set narrows the match, the matcher gives up. For
   pricing, any printing of the same card has approximately the same price --
   returning nothing is strictly worse than picking the first candidate.

2. **Refresh endpoint does not auto-canonize orphans.** 10 entries have a
   `card_id` but no MYP source card. The refresh endpoint returns 422 for
   these instead of attempting the canonize flow that already exists in the
   codebase.

## Affected Data

- 10 orphan entries (card_id set, no MYP SourceCard) -- fixed by T02
- 417 unlinked entries (card_id=NULL) -- improved match rate on next
  bulk-canonize via T01
- 124 already-linked entries -- no change

## Wave Breakdown

### Wave 0 (parallel -- no dependencies between tasks)

| Task | Description | Files |
|------|-------------|-------|
| T01  | Matcher best-effort + tests | `src/collection/matcher.py`, `tests/collection/test_matcher.py` |
| T02  | Refresh auto-canonize + tests | `src/api/routers/collection.py`, `tests/api/test_collection_canonize.py` (or new file) |

Both tasks touch independent files and can execute in parallel.

## Task List

- [x] **F55-T01** -- Matcher best-effort for ambiguous matches (done)
- [x] **F55-T02** -- Refresh auto-canonize for orphan entries (done)
