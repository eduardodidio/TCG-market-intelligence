# F125 — 3D Card Preview Universal

**Status:** planned
**Priority:** P1 (UX consistency + bugfix)
**Scope:** frontend-only (4 tasks, 1 wave)

## Goal

Unify the 3D tilt + click-to-zoom experience across the entire app.

### Bug found during planning

F116 added `Card3DTilt` to `CardTile`, `CatalogCardTile`, `DeckCardTile`, and
`CardHoverPreview` but **missed 5 inline tile components** that were defined
locally inside page files. These tiles still use the old `hover:scale-[1.02]`
CSS (or no scale at all) instead of `Card3DTilt`:

| Component | File | Problem |
|-----------|------|---------|
| `CollectionCardTile` | `MyCollection.tsx` | `hover:scale-[1.02]`, no 3D, no preview modal |
| `MarketplaceCardTile` | `Marketplace.tsx` | `hover:scale-[1.02]`, no 3D, no preview modal |
| `SharedCardTile` | `SharedCollectionPage.tsx` | `hover:scale-[1.02]`, no 3D, no preview modal |
| `WishlistCard` | `WishlistPage.tsx` | No scale, no 3D, no preview modal |
| `DuplicatesList` card | `DuplicatesList.tsx` | No scale, no 3D, no preview modal |

This is the most likely reason the user perceived "3D was working then stopped"
— the Cards/Catalog pages have 3D, but switching to Collection/Marketplace/
Wishlist shows flat tiles.

### New features (detail pages + treasure)

Additionally, the detail pages and treasure modal never had 3D:

1. **CardDetail** (`/cards/:id`) — plain `<img>`, no 3D, no click-to-zoom
2. **CollectionCardDetail** (`/collection/:id`) — plain `<img>`, no 3D, no click-to-zoom
3. **TreasureModal** — fly-in animation but no 3D tilt

## Affected Files

| Task | Files |
|------|-------|
| T01 (bugfix) | `MyCollection.tsx`, `Marketplace.tsx`, `SharedCollectionPage.tsx`, `WishlistPage.tsx`, `DuplicatesList.tsx` |
| T02 | `CardDetail.tsx` |
| T03 | `CollectionCardDetail.tsx` |
| T04 | `TreasureModal.tsx` |

## Wave Plan

| Wave | Tasks | Description |
|------|-------|-------------|
| 1    | T01, T02, T03, T04 | All parallel — no dependencies between them |

## Acceptance Criteria (feature-level)

- [ ] **Bugfix**: CollectionCardTile wrapped in Card3DTilt (remove hover:scale CSS)
- [ ] **Bugfix**: MarketplaceCardTile wrapped in Card3DTilt (remove hover:scale CSS)
- [ ] **Bugfix**: SharedCardTile wrapped in Card3DTilt (remove hover:scale CSS)
- [ ] **Bugfix**: WishlistCard wrapped in Card3DTilt
- [ ] **Bugfix**: DuplicatesList cards wrapped in Card3DTilt
- [ ] All 5 fixed tiles: click image opens CardPreviewModal with 3D zoom
- [ ] CardDetail: image wrapped in Card3DTilt, click image/name opens modal
- [ ] CollectionCardDetail: image wrapped in Card3DTilt, click image/name opens modal (foil-aware)
- [ ] TreasureModal: enlarged image wrapped in Card3DTilt with foil shimmer
- [ ] All existing tests pass, new tests cover interactions
- [ ] No new dependencies added
