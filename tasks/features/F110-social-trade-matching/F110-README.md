# F110 -- Social & Trade Matching

**Status:** planned

## Summary

Add a wishlist system (want-to-buy), automatic duplicate detection from
collections, and a trade matcher that cross-references wishlists against
duplicates across users to suggest potential trades.

## Scope

- **Wishlist** -- per-user, private list of desired cards (CRUD + mark acquired)
- **Duplicates** -- detect collection entries with quantity > 1, expose as
  "available for trade"
- **Trade Matcher** -- query that finds users whose duplicates match another
  user's wishlist, returns ranked suggestions

## Non-scope (future)

- Chat / messaging between users
- Real-time notifications for new matches
- Trade negotiation workflow (reuse existing TradeInterest flow for that)
- Public wishlist sharing

## Wave Plan

### Wave 0 -- DB Schema (sequential, blocks everything)

| Task | Description |
|------|-------------|
| T01  | Wishlist table + repository methods |

### Wave 1 -- Backend Services & API (parallel)

| Task | Description |
|------|-------------|
| T02  | Wishlist CRUD API endpoints |
| T03  | Duplicates detection endpoint |
| T04  | Trade matcher service + endpoint |

### Wave 2 -- Frontend (parallel)

| Task | Description |
|------|-------------|
| T05  | Wishlist page + "Add to Wishlist" button |
| T06  | Duplicates view + Trade Matches page |

## Dependencies

- Wave 0 blocks Wave 1
- Wave 1 blocks Wave 2
- T02, T03, T04 are independent of each other within Wave 1
- T05 depends on T02; T06 depends on T03 + T04

## Files expected to change

### New files
- `src/database/models.py` -- WishlistRow model (added to existing file)
- `src/services/trade_matcher.py` -- matching logic
- `src/api/routers/wishlist.py` -- wishlist CRUD
- `src/api/routers/trade_match.py` -- duplicates + match endpoints
- `src/api/schemas/wishlist.py` -- request/response schemas
- `src/api/schemas/trade_match.py` -- match result schemas
- `frontend/src/api/wishlist.ts` -- API client
- `frontend/src/api/tradeMatch.ts` -- API client
- `frontend/src/pages/WishlistPage.tsx`
- `frontend/src/pages/TradeMatchesPage.tsx`
- `frontend/src/components/AddToWishlistButton.tsx`
- `frontend/src/components/DuplicatesList.tsx`
- Test files for all of the above

### Modified files
- `src/database/models.py` -- add WishlistRow
- `src/database/repository.py` -- import WishlistRow for create_all
- `src/api/app.py` -- register new routers
- `frontend/src/App.tsx` -- add routes
- `frontend/src/components/Layout.tsx` -- nav links
- `frontend/src/i18n/locales/en.json` -- i18n keys
- `frontend/src/i18n/locales/pt-BR.json` -- i18n keys
- `README.md` -- feature note

## Estimated endpoint count after F110

22 routers, ~100 endpoints, 26 pages
