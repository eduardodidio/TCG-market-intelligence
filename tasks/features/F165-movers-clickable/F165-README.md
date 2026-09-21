# F165 — Collection Movers Clickable + Inspect

**Status:** completed
**Wave:** 0 (parallel with F164, F166, F167)
**Tasks:** 2
**Files touched:** `frontend/src/components/CollectionMovers.tsx`, tests

## Summary

MoverRow in the CollectionMovers dashboard panel is currently a non-clickable `<div>`. Users want to click on a mover to navigate to the card detail page and understand the price progression. The component already has `card_id` in the data.

## Tasks

| Task | Description | Wave |
|------|-------------|------|
| F165-T01 | Make MoverRow clickable with Link to card detail | 0 |
| F165-T02 | Tests for clickable movers | 0 |

## Architecture Notes

- MoverRow wraps content in `<Link to={/cards/${mover.card_id}}>`
- Add hover effect (bg highlight, cursor pointer)
- Keep existing layout (image, name, set, price change)
- Default limit stays at 5, expand buttons unchanged
