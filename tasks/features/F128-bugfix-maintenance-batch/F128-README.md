# F128 — Bugfix & Maintenance Batch

**Status:** planned
**Priority:** high
**Estimated tasks:** 3
**Waves:** 1 (all parallel)

## Summary

Three independent fixes:

1. **T01 — Remove PWA UpdatePrompt modal**: The "new version available" toast
   confuses users. Remove the UI component while keeping the SW auto-update.
2. **T02 — Fix CardPreviewModal backdrop click → navigation**: In
   MyCollection, the CardPreviewModal is rendered inside `inner` which is
   wrapped by `<Link>`. React synthetic events from the portal bubble through
   the React component tree to the Link, causing navigation on backdrop click.
3. **T03 — Collection wipe & re-import CLI**: Add a `import-csv` CLI command
   so the user can re-import their collection from `docs/exportColeacao.csv`.

## Root Cause Analysis (T02)

`CollectionCardTile` in `MyCollection.tsx` builds `inner` (JSX variable)
which includes `<Card3DTilt>` wrapping both the card content and the
`CardPreviewModal`. Then on line 249: `<Link to={...}>{inner}</Link>`.

With `createPortal`, React synthetic events bubble through the **React
component tree** (not the DOM tree). So clicks on the portal backdrop
bubble: `CardPreviewModal → Card3DTilt → inner → Link`. The Link intercepts
the click and navigates.

**Fix:** Move `CardPreviewModal` out of `inner` so it renders as a sibling
to `<Link>`, not inside it.

Other tile components (CardTile, CatalogCardTile, DeckCardTile, etc.)
already have the modal outside the Link — only MyCollection is affected.

## Wave Plan

| Wave | Tasks      | Rationale                        |
|------|------------|----------------------------------|
| 0    | T01,T02,T03 | All independent, zero overlap   |

## Files Affected

- T01: `frontend/src/components/UpdatePrompt.tsx` (delete),
  `frontend/src/components/Layout.tsx` (remove import+render),
  `frontend/src/components/__tests__/Layout.test.tsx` (remove mock)
- T02: `frontend/src/pages/MyCollection.tsx` (move modal outside Link)
- T03: `src/cli/main.py` (add `import-csv` command)
