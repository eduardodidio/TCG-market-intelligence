# F17: Collection Filter -- Set Symbol Icons

## Overview

Replace text-based set filter chips on the MyCollection page with
Scryfall set symbol icons. Tooltips show the full set name on hover.
Filtering behavior is unchanged.

**Type:** Frontend-only
**PRD:** `docs/prd/F17-set-symbol-icons.md`

## Wave Plan

### Wave 0 -- Utility (no dependencies)

| Task   | Title                           | Files                                          |
|--------|---------------------------------|------------------------------------------------|
| F17-T01 | Scryfall set icon URL utility  | `frontend/src/utils/scryfall.ts`, tests        |

### Wave 1 -- Component (depends on Wave 0)

| Task   | Title                           | Files                                          |
|--------|---------------------------------|------------------------------------------------|
| F17-T02 | SetIconFilter component        | `frontend/src/components/SetIconFilter.tsx`, tests |

### Wave 2 -- Integration (depends on Wave 1)

| Task   | Title                           | Files                                          |
|--------|---------------------------------|------------------------------------------------|
| F17-T03 | Wire SetIconFilter into MyCollection | `frontend/src/pages/MyCollection.tsx`, tests |

## Status: done

## Total: 3 tasks, 3 waves
