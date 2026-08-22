# F48 Nav & UX Polish

**Status: planned**

## Overview

Two independent, surgical fixes:

1. **Nav active state fix** -- Navigation items sharing URL prefixes incorrectly highlight together (e.g., /market and /market/trending both light up when visiting either page).
2. **Default collection sort** -- Collection page defaults to name/asc; user wants price/desc (highest price first).

## Wave Plan

### Wave 1 (parallel -- independent files)

| Task | Title | File(s) | Status |
|------|-------|---------|--------|
| T01 | Nav active state fix | `frontend/src/components/Layout.tsx` + tests | planned |
| T02 | Default sort: price desc | `frontend/src/pages/MyCollection.tsx` + tests | planned |

## Affected Routes (T01)

- `/market` vs `/market/trending`
- `/banlist` vs `/banlist/history`
- `/decks` vs `/decks/ranking`

## Risk

Low. Both changes are single-line edits with clear test coverage expectations.
