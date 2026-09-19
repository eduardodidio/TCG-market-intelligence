# F157 — Journey P2 Fixes (Friction)

**Status:** planned
**Branch:** homol
**Created:** 2026-09-18
**Source:** `docs/ux-journey-audit-2026-09-18.md` — P2 issues (after filtering false positives)

## Triage Notes

Many P2 items from the audit were already implemented:
- ~~MyCollection URL filters~~ — already syncs searchParams (lines 305-317, 573)
- ~~AcquisitionPriceInput feedback~~ — already has success checkmark (1.5s)
- ~~DeckBuildWizard back button~~ — already has step2/3/4-back buttons
- ~~ImportPurchasesPage collection link~~ — already has "Go to Collection" Link
- ~~UpdatePrompt~~ — component doesn't exist (vite-plugin-pwa handles it)
- ~~Admin credit adjustment~~ — already has error display + closes on success
- ~~Deck generation loading~~ — already shows "Generating..." on button
- ~~Login dark mode~~ — already permanently dark (bg-slate-900)
- ~~NotFoundPage~~ — uses slate colors that work in both modes

## Real P2 (3 tasks)

| Task | Title                                    | Files |
|------|------------------------------------------|-------|
| T01  | BetaRoute explanation text               | BetaRoute.tsx, i18n |
| T02  | ImportPurchasesPage i18n (result + overwrite) | ImportPurchasesPage.tsx, i18n |
| T03  | OfflineBanner last synced timestamp      | OfflineBanner.tsx, Layout.tsx, i18n |

## Wave Plan

### Wave 0 (parallel — no file conflicts)
- **T01**: Add explanation to BetaRoute blocked screen
- **T02**: Translate hardcoded English in ImportPurchasesPage
- **T03**: Show "Last synced X ago" in OfflineBanner when offline

**Total: 3 tasks in 1 wave**
