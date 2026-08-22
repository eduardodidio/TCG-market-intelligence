# F31 — Set Icon Filter Scroll & Image Icons

**Status:** planned
**Created:** 2026-08-21

## Summary

Improve the SetIconFilter component: limit visible icons to ~10 with horizontal
scroll, and ensure set icons use Scryfall image URLs (already implemented via
`scryfallSetIconUrl`).

## User Story

As a collector with cards from many sets, I want the set filter to be compact
and scrollable so it doesn't overwhelm the page when I have 30+ sets.

## Architecture

### Current State

- `SetIconFilter` already uses `overflow-x-auto` but has no max-width constraint
  so it stretches to show all icons
- Icons already use `scryfallSetIconUrl` (Scryfall SVG images) via `<img>` tags
- Fallback to text abbreviation on image error already works

### Changes

- Add `max-width` or fixed container width to show ~10 icons at a time
- Add visible scroll indicator (gradient fade on edges, or scroll arrows)
- Style the scrollbar for dark theme (thin, semi-transparent)
- The icon images are already Scryfall SVGs — no change needed there

### Frontend Only

- Modify `SetIconFilter.tsx` — add constrained width + scroll styling
- Optional: add left/right scroll arrow buttons for better UX
- CSS-only changes, no backend work

## Constraints

- Must remain responsive (mobile shows fewer icons, desktop ~10)
- "All" button stays visible and pinned at the start
- Scroll position resets when filter options change
- Accessibility: keyboard scrollable

## Tasks

| Task | File | Wave | Description |
|------|------|------|-------------|
| T01 | F31-T01.md | 1 | SetIconFilter: constrained width + scroll styling |
| T02 | F31-T02.md | 1 | SetIconFilter: scroll arrow buttons (left/right) |
| T03 | F31-T03.md | 2 | Tests + visual polish |

## Waves

- **Wave 1** (2 tasks, parallel): T01 (scroll container), T02 (arrow buttons)
- **Wave 2** (1 task): T03 (tests)

## File Conflicts

- `frontend/src/components/SetIconFilter.tsx` — main changes (isolated component)
- No other file conflicts
