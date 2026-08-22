# F47 Search PT Name Fallback

## Status: planned

## Overview

MYP Cards search sometimes fails to find cards by English name (e.g., "Abrade"
returns zero results, but the card exists as "Abrasao" in Portuguese). The sync
pipeline currently only searches by `name_en` and never attempts `name_pt`.

This feature adds a Portuguese-name fallback to the search and matching
pipeline so that cards unreachable by English name can still be matched.

## Scope

1. Add `name_pt` field to the `CollectionEntry` dataclass.
2. Propagate `name_pt` through `row_to_collection_entry()`.
3. Extend the matcher to compare search-result names against both `name_en`
   and `name_pt`.
4. In the sync pipeline, retry the MYP search with `name_pt` when the
   `name_en` search returns zero results.
5. Log when the PT fallback is used.

## Wave Plan

| Wave | Task | Description | Depends On |
|------|------|-------------|------------|
| 1 | T01 | Add `name_pt` to `CollectionEntry` + converter | -- |
| 1 | T02 | Matcher `name_pt` comparison | -- |
| 2 | T03 | Sync pipeline PT fallback search | T01, T02 |

## Files Modified

- `src/collection/matcher.py` -- `CollectionEntry` dataclass, `_try_name_match`
- `src/collection/converter.py` -- `row_to_collection_entry`
- `src/collectors/sync_collection.py` -- `_process_single_entry`
- `tests/collection/test_matcher.py`
- `tests/collection/test_converter.py`
- `tests/collectors/test_sync_collection.py`

## Risk

Low. Changes are additive (new optional field, fallback path). Existing
EN-name matching is untouched when `name_pt` is None.
