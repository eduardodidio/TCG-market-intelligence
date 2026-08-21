# F20 -- Card Grid Size Control

**Status:** done
**Created:** 2026-08-21
**Type:** frontend-only

## Summary

Add a 3-option grid size toggle (Small / Medium / Large) to the
collection page header. Persist the preference in localStorage. Medium
is the current default. This is entirely frontend -- no backend changes.

## Key Observations

The current grid classes in `MyCollection.tsx` (lines 288, 307):
```
grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6 gap-4
```
This is used in two places: the skeleton grid and the card grid. Both
must respond to the size setting.

The `CollectionCardTile` component is defined inline in
`MyCollection.tsx`. For the Small size, the info section should be
condensed (name + price only, no set/rarity/quality row).

## Wave Plan

| Wave | Tasks | Rationale |
|------|-------|-----------|
| 0 | T01 | Hook + constants (shared dependency for T02 and T03) |
| 1 | T02, T03 | Toggle component (T02) and grid integration (T03) in parallel |
| 2 | T04 | Tests for all new code |

## Tasks

- **F20-T01** -- useGridSize hook and grid size constants
- **F20-T02** -- GridSizeToggle component
- **F20-T03** -- Integrate grid size into MyCollection page
- **F20-T04** -- Tests for hook, toggle component, and page integration

## Files Likely Affected

- `frontend/src/hooks/useGridSize.ts` (new)
- `frontend/src/utils/constants.ts` (add grid config)
- `frontend/src/components/GridSizeToggle.tsx` (new)
- `frontend/src/pages/MyCollection.tsx` (modify grid classes + card tile)
- `frontend/tests/hooks/useGridSize.test.ts` (new)
- `frontend/tests/components/GridSizeToggle.test.tsx` (new)
- `frontend/tests/pages/MyCollection.test.tsx` (extend)
