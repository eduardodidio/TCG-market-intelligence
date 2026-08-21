# F15 -- Collection Display Fixes

**Status:** planned
**Created:** 2026-08-20
**Type:** hotfix batch

## Summary

Three display fixes for the collection experience:

1. **Full-art card images not loading** -- MYP uses non-standard set codes for
   variant printings (borderless, extended art, showcase, Secret Lair, etc.).
   Scryfall URLs built with these codes return 404. A mapping layer is needed
   to translate MYP variant set codes to Scryfall-compatible set codes, plus
   a more robust fallback chain.

2. **BRL currency indicator in sidebar** -- Add a "BRL" currency label with
   the Brazilian flag in the sidebar/navigation to make the active currency
   clear. All price values already format correctly via `formatBRL()`.

3. **Collection card detail missing values** -- When clicking a collection
   card, the detail view should show collection-specific metadata (quantity,
   quality, language, extras, set name) alongside price data. Currently
   linked cards open the generic CardDetail page (which lacks collection
   context), and unlinked cards redirect to the Explore page (which often
   shows no results).

## Root Cause Analysis

### HF-A: Full-Art Images
The CSV import stores MYP-specific variant set codes like:
- `bldmr` (Borderless Dominaria Remastered) -- Scryfall uses `dmr`
- `exdmu` (Extended Art Dominaria United) -- Scryfall uses `dmu`
- `bl2x2` (Borderless Double Masters 2022) -- Scryfall uses `2x2`
- `bltr` / `blltr` / `srltr` (LTR variants) -- Scryfall uses `ltr`
- `sld158` (Secret Lair Drop) -- Scryfall uses `sld`
- `eafic` / `eahoc` (Extended Art) -- Scryfall uses `fic` / `hoc`
- And many more (`bbfdn`, `blfdn`, `cbznr`, `cthb`, `feclb`, etc.)

Both `_scryfall_image_url()` (backend) and `scryfallImageUrl()` (frontend)
build URLs like `api.scryfall.com/cards/bldmr/437` which 404.

The frontend has a fallback to `scryfallImageByName()` but it only fires
on `onError` and depends on `name_en` being available.

### HF-B: Currency Indicator
The `formatBRL()` utility already outputs `R$ X.XXX,XX` correctly. No price
formatting bugs found. The missing piece is a visible currency indicator in
the sidebar/header so users always know what currency they are seeing.

### HF-C: Collection Card Detail
Two problems:
1. **Linked cards** (`card_id != null`): Navigate to `/cards/{card_id}` which
   shows the generic `CardDetail` page. This page has no collection-specific
   data (quantity, quality, language, extras).
2. **Unlinked cards** (`card_id == null`): Navigate to `/cards?name=X&set=Y`
   (Explore page). Since the card may not exist in the `cards` table at all,
   the Explore page often shows "No cards found" -- a dead end for the user.

## Wave Plan

| Wave | Tasks | Rationale |
|------|-------|-----------|
| 0 | T01 | Shared utility: MYP-to-Scryfall set code mapping (used by T02, T03) |
| 1 | T02, T03, T04 | Independent fixes: images (T02), currency (T03), detail view (T04) |

## Tasks

- **F15-T01** -- MYP variant set code mapping utility
- **F15-T02** -- Fix full-art card images using set code mapping + fallback
- **F15-T03** -- Add BRL currency indicator to sidebar
- **F15-T04** -- Collection card detail view with collection metadata

## Files Likely Affected

### T01 (mapping utility)
- `frontend/src/utils/setCodeMap.ts` (new)
- `src/utils/set_code_map.py` (new, backend equivalent)

### T02 (images)
- `frontend/src/utils/scryfall.ts`
- `frontend/src/pages/MyCollection.tsx` (CollectionCardTile)
- `frontend/src/components/CardTile.tsx`
- `src/api/routers/collection.py` (`_scryfall_image_url`)

### T03 (currency indicator)
- `frontend/src/components/Layout.tsx`

### T04 (collection detail)
- `frontend/src/pages/CollectionCardDetail.tsx` (new)
- `frontend/src/api/collection.ts`
- `src/api/routers/collection.py` (new endpoint)
- `src/api/schemas/collection.py`
- Router config (App.tsx or routes file)
