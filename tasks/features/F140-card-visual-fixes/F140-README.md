# F140 — Card Visual Fixes (Arkenstone Art + White Corners)

**Status:** planned
**Created:** 2026-09-18
**Priority:** P1

## Summary

Two visual bugs:

1. **Arkenstone art card image missing** — "The Arkenstone // Seek the Heart
   (Art Card with Signature)" (set `ashob`, collector `44a`) has `image_uri=NULL`
   because Scryfall doesn't include art series cards in bulk data. Need a
   fallback to the regular card's image (`hob` set).
2. **White corners on card images** — Container has `rounded-lg` but `<img>`
   elements don't, causing white/dark background to bleed through corners
   in CardTile, CatalogCardTile, and DeckCardTile.

## Scope

| In scope | Out of scope |
|----------|--------------|
| Fallback image for art cards (image_uri NULL) | Fetching art card-specific images |
| Fix rounded corners on card img elements | Redesigning card grid layout |
| CardTile, CatalogCardTile, DeckCardTile, CardImage | CardHoverPreview, CardPreviewModal (already correct) |

## Architecture

### Bug 1 — Arkenstone / Art Card Image Fallback

The card exists in the DB as `set_code='ashob', collector_number='44a'` with
`image_uri=NULL`. Scryfall has the regular version at `set_code='hob'`.

**Fix approach**: In the CardImage component or the API response, when
`image_uri` is NULL, try constructing a Scryfall URL from the card's set code
and collector number. For art series cards (set codes starting with `as` +
base set), strip the `as` prefix and use the base set code.

Alternatively, in the catalog API or seeder, populate `image_uri` using a
fallback: `https://api.scryfall.com/cards/{set}/{number}?format=image&version=normal`.
For art cards, strip the art series prefix from the set code.

Simplest fix: **Frontend CardImage fallback** — if `image_uri` is null but
the card has `set_code` and `collector_number`, construct a Scryfall image URL
as fallback. Art card set codes like `ashob` map to base set `hob` via the
existing `set_code_map.py`.

### Bug 2 — White Corners

Add `rounded-lg` to `<img>` elements in:
- `CardTile.tsx` (line ~251)
- `DeckCardTile.tsx` (line ~42)
- `CardImage.tsx` (line ~40) — the reusable component used by CatalogPage

This ensures the image corners match the container's `rounded-lg`.

## Tasks

| ID | Title | Wave | Depends on |
|----|-------|------|------------|
| T01 | Fix white corners on card images (CSS) | 0 | -- |
| T02 | Art card image fallback (Scryfall URL construction) | 0 | -- |

## Waves

- **Wave 0**: T01 + T02 (parallel — T01 is pure CSS, T02 is component logic)

## Risks

- Scryfall rate limits on constructed URLs (low risk — images are cached by browser)
- Art card collector numbers may not match Scryfall's (e.g. `44a` vs `44`)
