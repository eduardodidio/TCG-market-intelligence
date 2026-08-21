# PRD F16 — Explore Cards: Sorting Fields

**Status:** planned
**Author:** Architect agent
**Date:** 2026-08-21

## Problem

The My Collection page (Explore Cards) lists cards in insertion order (by
database row ID). Users cannot reorder the grid by name, price, set, or
other meaningful attributes. This makes it hard to find the most valuable
cards, browse by set, or locate recently added entries.

## Goal

Add a sort control to the collection grid so users can order cards by any
of the supported fields in ascending or descending direction.

## Sort Fields

| Field key          | Label (UI)          | DB column(s)                        | Default dir |
|--------------------|---------------------|-------------------------------------|-------------|
| `name`             | Name                | `user_collection.name_en`           | asc         |
| `price`            | Price               | latest_price (derived)              | desc        |
| `set`              | Set / Edition       | `user_collection.set_code`          | asc         |
| `number`           | Card Number         | `user_collection.collector_number`  | asc         |
| `added`            | Date Added          | `user_collection.created_at`        | desc        |

**Default sort:** `name` ascending (A-Z).

### Price sorting caveat

`latest_price` is not a column on `user_collection` -- it is derived by
joining through `source_cards` and `price_observations`. Server-side
price sorting would require a complex join or denormalization. For the
initial implementation, **price sorting will be done client-side** on the
currently loaded cards. This is acceptable because:
- The collection is finite (~200-500 cards for a typical user)
- Infinite scroll already loads cards incrementally
- A future feature can add a denormalized `cached_price` column if needed

All other sort fields are direct columns on `user_collection` and will be
sorted server-side.

## Pagination Impact

The current pagination uses cursor-based `after_id` which assumes
ordering by `id ASC`. When sorting by a different field, the cursor
approach breaks. Two options:

1. **Offset-based pagination** when sort != default -- simpler, slight
   performance cost on large collections (acceptable for ~500 cards).
2. **Keyset pagination** on the sort column -- more complex, not needed
   at this scale.

Decision: use **offset-based pagination** (`page` param) when a non-default
sort is active. Keep cursor-based for the default (name) sort. Actually,
for simplicity, switch entirely to offset-based pagination for this
endpoint. The collection size (~500 cards) does not warrant cursor
optimization.

## API Changes

`GET /api/v1/collection`

New query parameters:
- `sort_by`: enum string, one of `name`, `set`, `number`, `added`.
  Default: `name`.
- `sort_dir`: `asc` or `desc`. Default depends on `sort_by` (see table).
- `offset`: integer >= 0. Replaces `cursor` for pagination. Default: 0.

The `cursor` parameter remains supported for backward compatibility but is
ignored when `offset` is provided.

Response: the `meta.cursor` field will still be populated for backward
compatibility. A new `meta.offset` field is added.

## Frontend Changes

- Add a `<SortSelect>` dropdown component above the card grid, next to
  the search bar.
- Options: Name (A-Z), Name (Z-A), Set, Card Number, Date Added (Newest),
  Date Added (Oldest), Price (High-Low), Price (Low-High).
- Price sort is applied client-side after fetching.
- All other sorts pass `sort_by` and `sort_dir` to the API.
- Sort selection is persisted in URL search params (`sort`, `dir`).
- Changing the sort resets the card list and offset to 0.

## Out of Scope

- Server-side price sorting (requires denormalization or complex join)
- Persisting sort preference in user settings
- Multi-column sort
- Buy price sorting (no buy price data in user_collection)

## Success Criteria

- Users can sort their collection by name, set, card number, and date added
  via a dropdown control.
- Users can sort by price (client-side) in both directions.
- Sort preference is reflected in the URL for shareability / back button.
- Infinite scroll / load-more continues to work with all sort options.
- Existing tests pass; new tests cover sort parameters.
