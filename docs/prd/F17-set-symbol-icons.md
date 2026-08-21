# PRD: F17 -- Collection Filter: Set Symbol Icons

## Problem

The collection page set filter currently displays text labels (e.g.
"DMR -- Dominaria Remastered") as horizontal pill-shaped chips. With many
sets in a collection, the text chips are hard to scan visually and take
excessive horizontal space, requiring scrolling.

## Solution

Replace the text-based set filter chips with compact Scryfall set symbol
icons. Each chip shows only the set's SVG icon. On hover, a tooltip
displays the full set name and card count. The filtering behavior stays
identical -- clicking a set icon filters the collection to that set,
clicking again (or "All") clears the filter.

## Scope

**Frontend-only change.** No backend modifications required.

### In Scope

- New utility function `scryfallSetIconUrl(setCode)` that maps MYP set
  codes to Scryfall set icon SVG URLs using the existing
  `mapToScryfallSetCode` mapping.
- New `SetIconFilter` component that renders set icons with tooltips
  instead of text labels. Keeps the same `selected`/`onSelect` interface
  as `FilterChips`.
- Update `MyCollection.tsx` to use `SetIconFilter` instead of
  `FilterChips` for the set filter.
- Graceful fallback: if the SVG fails to load, show the set code text.
- Tests for the new utility and component.

### Out of Scope

- Changing `FilterChips` itself (it is used by `Cards.tsx` and should
  remain text-based there).
- Backend changes to the `/api/v1/collection/sets` endpoint.
- Caching or prefetching set icons.

## Technical Notes

### Scryfall Set Icon URL

Scryfall hosts set symbol SVGs at a predictable URL pattern:

```
https://svgs.scryfall.io/sets/{set_code}.svg
```

The set code must be the standard Scryfall code (lowercase). The existing
`mapToScryfallSetCode()` function in `frontend/src/utils/setCodeMap.ts`
handles the MYP-to-Scryfall translation.

### Component Design

The `SetIconFilter` component should:

1. Render an "All" button (same style as current FilterChips "All").
2. For each set option, render a clickable icon button containing:
   - An `<img>` tag loading the Scryfall SVG (with `alt` = set name).
   - A CSS/HTML tooltip on hover showing `"{set_name} ({count})"`.
3. Highlight the selected icon (e.g., cyan ring/background).
4. Handle SVG load errors by falling back to the set code text.
5. Match the existing horizontal scrollable layout.

### Data Available from Backend

The `/api/v1/collection/sets` endpoint already returns:

```json
[
  { "set_code": "DMR", "set_name": "Dominaria Remastered", "count": 42 },
  { "set_code": "MH2", "set_name": "Modern Horizons 2", "count": 15 }
]
```

All data needed for icons and tooltips is already available.

## Success Criteria

- Set filter shows SVG icons instead of text labels.
- Hovering an icon shows a tooltip with the full set name.
- Clicking an icon filters the collection (same behavior as before).
- SVG load errors fall back to text gracefully.
- All existing FilterChips tests still pass (component unchanged).
- New tests cover SetIconFilter rendering, selection, tooltip, and
  fallback behavior.
