# F182 — BanBadge tooltip with banned formats on portfolio card tiles

**Status:** done
**Branch:** homol
**Complexity:** Small (3 tasks, 2 waves)

## Problem

On the MyCollection page, each card tile shows a BanBadge ("Banned" or
"Restricted") but provides NO information about WHICH formats the card is
banned or restricted in. Users must navigate to the card detail page to
discover this. The backend API already returns per-format ban data, but the
frontend discards it during aggregation.

### Current Behavior

1. `fetchCollectionBanned()` returns `BannedCollectionCard[]` with one row
   per card+format combination (e.g., Sol Ring appears once for "commander"
   and once for "legacy").
2. `bannedCardMap` in `MyCollection.tsx` (line 525) aggregates to
   `Map<number, { status, recentlyChanged }>`, keeping only the worst
   status per card_id. The per-format detail is lost.
3. `BanBadge.tsx` receives only `status` and `recentlyChanged` -- it has
   no knowledge of formats.

### Desired Behavior

1. `bannedCardMap` also collects an array of `{ format, status }` per
   card_id so the format breakdown is preserved.
2. `BanBadge` accepts an optional `formats` prop and renders a native
   tooltip (via `title` attribute) listing each format and its status.
3. No backend changes required.

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/pages/MyCollection.tsx` | Enhance `bannedCardMap` to include `formats` array; pass to `CollectionCardTile` and `BanBadge` |
| `frontend/src/components/BanBadge.tsx` | Accept optional `formats` prop; render `title` tooltip with format list |
| `frontend/src/i18n/locales/en.json` | Add `banEngine.tooltipFormat` key |
| `frontend/src/i18n/locales/pt-BR.json` | Add `banEngine.tooltipFormat` key |
| `frontend/tests/components/BanBadge.test.tsx` | Add tooltip rendering tests |

## Task List

| Task | Title | Wave | Depends |
|------|-------|------|---------|
| T01 | PRD + diagrams | W0 | -- |
| T02 | Enhance bannedCardMap in MyCollection to collect formats array | W1 | T01 |
| T03 | BanBadge tooltip with formats list + i18n + tests | W1 | T01 |

## Wave Plan

### Wave 0
- **T01** -- Create PRD under `docs/prd/` and update diagrams under
  `docs/diagrams/`. Lightweight docs-only wave.

### Wave 1 (T02 + T03 in parallel)
- **T02** changes `MyCollection.tsx` only: the `bannedCardMap` type grows
  from `{ status, recentlyChanged }` to
  `{ status, recentlyChanged, formats: Array<{ format: string; status: string }> }`.
  The `CollectionCardTile` function signature gains a `banFormats` prop
  and passes it to `BanBadge`.
- **T03** changes `BanBadge.tsx` only: accepts optional `formats` prop,
  builds a `title` string from the array, and renders it on the outer
  `<span>`. Adds i18n keys and test coverage.

T02 and T03 touch different files and can run in parallel. T03 adds the
optional `formats` prop (BanBadge still works without it), so there is no
blocking dependency.

## Acceptance Criteria

1. Hovering over a BanBadge on MyCollection shows a native browser tooltip
   listing all formats where the card is banned/restricted.
2. The tooltip text is internationalized (EN and PT-BR).
3. BanBadge continues to work unchanged when `formats` is not provided
   (backward compatible).
4. No new dependencies introduced.
5. No backend changes.
6. Existing BanBadge tests pass; new tests cover the tooltip behavior.

## Parallel Compatibility

FULLY INDEPENDENT from F180 (catalog), F181 (alert link), F183 (card detail).
Only touches `BanBadge.tsx` and `MyCollection.tsx` -- no overlap with other
features in the F180-F183 batch.
