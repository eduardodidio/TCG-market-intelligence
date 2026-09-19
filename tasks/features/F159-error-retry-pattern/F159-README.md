# F159 — Error Retry Pattern (Systematic)

**Status:** planned
**Branch:** homol
**Created:** 2026-09-18
**Source:** `docs/ux-audit-2026-09-18.md` + `docs/ux-journey-audit-2026-09-18.md`

## Summary

10 pages show errors without retry capability. `ErrorBanner` component
already exists with `onRetry` prop — most pages just need to use it.

## Audit Results

**Already correct (5 pages):** CardDetail, SharedCollectionPage, Marketplace,
CollectionCardDetail, MyTrades, MarketMovers — all use `<ErrorBanner onRetry={...} />`

**Need fix (10 pages):**
- ErrorBanner present but missing onRetry: Cards.tsx, CatalogPage.tsx
- Inline error div without retry: DeckList, DeckView, DeckBuildWizard,
  TopDecksPage, Evaluations, AchievementsPage, AdminPanel, ImportPurchasesPage

## Tasks

| Task | Title                                    | Files |
|------|------------------------------------------|-------|
| T01  | Add onRetry to existing ErrorBanner uses | Cards.tsx, CatalogPage.tsx |
| T02  | Deck pages: replace inline → ErrorBanner | DeckList.tsx, DeckView.tsx, DeckBuildWizard.tsx |
| T03  | Other pages: replace inline → ErrorBanner| TopDecksPage.tsx, Evaluations.tsx, AchievementsPage.tsx |

Note: AdminPanel and ImportPurchasesPage have form-specific inline errors
that are appropriate (validation feedback, not page-level errors). Skipped.

## Wave Plan

### Wave 0 (parallel — no file conflicts)
- **T01**: Add `onRetry={refetch}` to Cards.tsx and CatalogPage.tsx ErrorBanner
- **T02**: Replace inline error divs in deck pages with ErrorBanner + retry
- **T03**: Replace inline error divs in other pages with ErrorBanner + retry

**Total: 3 tasks in 1 wave**
