# F51 — Fix Explore Cards (Images, Prices, Refresh)

**Status:** done
**Priority:** high (UX bug fix)
**Dependencies:** none

## Summary

Many cards in the Explore Cards page (`/cards`) show no image and some show
no price. The card detail page (`CardDetail.tsx`) lacks the dual-fallback
image logic that `CardTile.tsx` already has. Additionally, cards that are
also in the user's collection should have a refresh button on the detail
page to manually fetch updated data from MYP.

## Root Cause Analysis

1. **Missing images on detail page**: `CardDetail.tsx` hides the image on
   error (`setImgError(true)`) but has NO fallback to `scryfallImageByName`
   — unlike `CardTile.tsx` which has a 3-tier fallback (primary → name →
   placeholder).
2. **Missing images on tiles**: `CardTile.tsx` already has fallback logic,
   but cards with `null` set_code AND `null` name_en will show placeholder.
   This is a data issue, not a code issue.
3. **Missing prices**: Cards without MYP linkage (`card_id` not in
   `price_observations`) return `latest_price: null`. This is a data
   coverage issue (140/349 cards). The refresh button helps users
   trigger a manual fetch.
4. **No refresh on explore detail**: The existing `POST
   /collection/{entry_id}/refresh` only works for collection entries.
   Explore cards need a way to refresh if the card is in the collection.

## Waves

### Wave 0 (parallel)
- **F51-T01** — Fix CardDetail image fallback
- **F51-T02** — Fix dashboard card detail & explore detail price display

### Wave 1
- **F51-T03** — Add refresh button on CardDetail for collection-linked cards
