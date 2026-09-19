# F158 — Journey P3 Fixes (Polish)

**Status:** planned
**Branch:** homol
**Created:** 2026-09-18
**Source:** `docs/ux-journey-audit-2026-09-18.md` — P3 issues (after filtering false positives)

## Triage Notes

Most P3 items were already implemented or too complex:
- ~~Commander search preview~~ — already has images with loading="lazy"
- ~~Budget input label~~ — already uses i18n `deckBuild.budgetLabel`
- ~~DeckView period selector i18n~~ — already uses `t()`
- ~~DeckView owned status~~ — DeckCardTile already has in_collection overlay + "Not Owned" badge
- ~~Admin audit log~~ — too complex for polish batch
- ~~Offline write queue~~ — too complex, needs architecture
- ~~Unsaved changes warning~~ — too complex, needs form state tracking
- ~~Guest user indicator~~ — moderate complexity, deferred

## Real P3 (3 tasks)

| Task | Title                                    | Files |
|------|------------------------------------------|-------|
| T01  | Card detail cross-links (Market/Trending)| CardDetail.tsx, i18n |
| T02  | Login OAuth section cleanup              | Login.tsx, i18n |
| T03  | Settings remove empty placeholders       | Settings.tsx |

## Wave Plan

### Wave 0 (parallel — no file conflicts)
- **T01**: Add "See on Market" / "View Trends" links to CardDetail
- **T02**: Hide disabled OAuth buttons, keep "or continue with" as future note
- **T03**: Remove empty "API Keys" and "Data Export" placeholder sections

**Total: 3 tasks in 1 wave**
