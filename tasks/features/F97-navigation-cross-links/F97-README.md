# F97 -- Navigation & Cross-Links

**Status:** planned
**Branch:** homol
**Type:** frontend-only

## Problem

Breadcrumbs are inconsistent (only 4 of 15+ secondary pages use them). Market
and Trending pages are disconnected. Trending cards show no ownership
indicator. Non-owned deck cards are dead ends. CardDetail (explore) has no
"Add to Collection" CTA.

## Goals

1. Add breadcrumbs to all secondary pages missing them
2. Cross-link Market and Trending bidirectionally
3. Collection ownership badge on trending/market cards
4. "Add to Collection" CTA on CardDetail for non-owned cards
5. "Add Missing Cards" batch button on DeckView
6. i18n for all new strings (EN + PT-BR)

## Task List

| Task | Title | Wave | Depends On |
|------|-------|------|------------|
| T01 | Breadcrumbs on all remaining secondary pages | 0 | -- |
| T02 | Market-Trending cross-links | 1 | T01 |
| T03 | Ownership badge on trending cards | 1 | -- |
| T04 | "Add to Collection" CTA on CardDetail | 2 | -- |
| T05 | "Add Missing Cards" on DeckView | 2 | -- |
| T06 | i18n keys (EN + PT-BR) | 2 | T01-T05 |

## Waves

**Wave 0 (T01):** Breadcrumbs on all secondary pages. Mechanical, no new
components -- import existing `Breadcrumb` and add to 11 pages.

**Wave 1 (T02, T03):** Cross-links between Market/Trending + ownership badge.
T02 adds navigation links. T03 adds a small badge to TrendingListItem and
TrendingCard. These are independent of each other.

**Wave 2 (T04, T05, T06):** Action CTAs on CardDetail and DeckView, plus
i18n consolidation. T04 and T05 are independent. T06 must run last to
collect all new strings.

## Files Likely Touched

- `frontend/src/pages/MarketPage.tsx`
- `frontend/src/pages/Trending.tsx`
- `frontend/src/pages/BanList.tsx`
- `frontend/src/pages/BanHistory.tsx`
- `frontend/src/pages/Settings.tsx`
- `frontend/src/pages/AdminPanel.tsx`
- `frontend/src/pages/Evaluations.tsx`
- `frontend/src/pages/TopDecksPage.tsx`
- `frontend/src/pages/Marketplace.tsx`
- `frontend/src/pages/ChangePassword.tsx`
- `frontend/src/pages/DeckList.tsx`
- `frontend/src/pages/CardDetail.tsx`
- `frontend/src/pages/DeckView.tsx`
- `frontend/src/components/TrendingListItem.tsx`
- `frontend/src/components/TrendingCard.tsx`
- `frontend/src/components/TrendingSection.tsx`
- `frontend/src/components/BatchAddModal.tsx` (may need initialText prop)
- `frontend/src/i18n/locales/en.json`
- `frontend/src/i18n/locales/pt-BR.json`
- `frontend/src/types/api.ts` (TrendingCardEntry -- may need collection_entry_id)
