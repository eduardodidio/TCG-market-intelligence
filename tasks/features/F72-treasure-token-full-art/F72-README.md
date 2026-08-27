# F72 — Treasure Token Full Art Display

**Status:** planned
**Wave structure:** Wave 0 (parallel with F73, F76)
**Dependencies:** None

## Summary

Replace the tiny 8x8 circle treasure image in the sidebar with the full treasure art displayed prominently. On click, open a modal showing the full-size treasure image and the token count.

## Tasks

| Task | Description | Wave |
|------|-------------|------|
| F72-T01 | Treasure sidebar art expansion + click modal | 0 |
| F72-T02 | Frontend tests | 0 |

## Acceptance Criteria

- Treasure art is shown fully in sidebar (not cropped into a circle)
- Clicking treasure opens a modal/overlay with full-size art + token count
- Modal dismisses on click outside or Escape key
- Language-aware image (EN/PT) still works
- All existing treasure tests pass + new modal tests
