# F130 -- UX: Foil Enhancement, Card Corners, Price Request Queue

**Status:** planned
**Branch:** homol

## Problem Statement

Three independent UX/backend improvements:

**A. Foil Visual Enhancement**: When inspecting a foil card in the 3D preview
(CardPreviewModal), the foil effect is barely noticeable. The `foil-shimmer.css`
exists but is too subtle, and CardTile/CatalogCardTile/DeckCardTile hardcode
`foil={false}` and don't pass `isFoil` to CardPreviewModal at all. The
`CollectionCard` type already has `is_foil: boolean` from the backend.

**B. Card Corner Rounding Fix**: When cards are inspected in the 3D preview,
white corners are visible because `overflow: hidden` is not applied at all
levels of the Card3DTilt / react-parallax-tilt / foil-shimmer wrapper chain.
The `rounded-lg` (~8px) is also too small for realistic Magic card corners.

**C. Price Update Request Queue**: The `POST /cards/{id}/refresh-price`
endpoint calls Liga directly via Playwright, which is unavailable on the
Render server. Users clicking refresh get errors. Solution: queue requests
in a new `price_update_requests` table, show "request queued" feedback, and
process the queue locally via CLI/cron (Windows Task Scheduler).

## Acceptance Criteria

### Feature A (Foil)
- Foil cards show vivid holographic/rainbow effect in CardPreviewModal
- Effect reacts to mouse tilt (not just hover)
- CardTile, CatalogCardTile, DeckCardTile pass `isFoil` to CardPreviewModal
- Non-foil cards remain unchanged

### Feature B (Corners)
- No white corners visible in 3D preview (CardPreviewModal)
- Card corners match realistic Magic card rounding (~3-4% radius)
- Fix applied to Card3DTilt, foil-shimmer wrapper, and image element
- No regression in CardTile, CatalogCardTile, DeckCardTile thumbnails

### Feature C (Price Queue)
- Clicking refresh queues a request instead of calling Liga directly
- User sees "request queued" feedback message
- Admin panel shows pending/processed requests
- CLI command `process-price-requests` processes the queue via Liga
- Credit is charged at request time (not processing time)
- Duplicate requests for same card within 24h are deduplicated

## Wave Strategy

### Wave 0 -- Frontend Visual (3 tasks, parallel)
All three are independent frontend tasks.

| Task | Description | Feature |
|------|-------------|---------|
| T01  | Enhanced foil shimmer CSS + Card3DTilt improvements | A |
| T02  | Propagate isFoil from CollectionCard to CardPreviewModal | A |
| T03  | Fix card corner rounding in Card3DTilt and CardPreviewModal | B |

### Wave 1 -- Backend Queue (2 tasks, parallel)
Backend model + endpoint changes, independent of Wave 0 frontend.

| Task | Description | Feature |
|------|-------------|---------|
| T04  | price_update_requests table + repository methods | C |
| T05  | Refactor refresh-price endpoint to queue + CLI processor | C |

### Wave 2 -- Frontend Queue + Admin (2 tasks, parallel)
Depends on Wave 1 API being defined.

| Task | Description | Feature |
|------|-------------|---------|
| T06  | Frontend: queued feedback on refresh + request status | C |
| T07  | Admin panel: price requests section | C |

## Key Files

### Feature A + B (Frontend)
- `frontend/src/styles/foil-shimmer.css` -- shimmer effects
- `frontend/src/components/Card3DTilt.tsx` -- 3D tilt wrapper
- `frontend/src/components/CardPreviewModal.tsx` -- preview modal
- `frontend/src/components/CardTile.tsx` -- collection card tile
- `frontend/src/pages/CatalogPage.tsx` -- CatalogCardTile
- `frontend/src/components/DeckCardTile.tsx` -- deck card tile

### Feature C (Backend)
- `src/database/models.py` -- SQLAlchemy models
- `src/api/routers/cards.py` -- refresh-price endpoint
- `src/api/routers/admin.py` -- admin endpoints
- `src/cli/main.py` -- CLI commands
- `frontend/src/api/cards.ts` -- frontend API calls
- `frontend/src/components/CardTile.tsx` -- refresh button UX
- `frontend/src/pages/AdminPanel.tsx` -- admin sections

## Constraints

- Liga requires Playwright (residential IP only) -- cannot run on Render
- Credit charged at request time, not at processing time
- react-parallax-tilt controls its own DOM -- overflow clipping needs care
- `CollectionCard.is_foil` already exists in frontend types (from backend)
- `CardSummary` does NOT have is_foil -- only CollectionCard does
