# T06 — Fix Mox Amber Art Card Image Fallback

**Status:** planned
**Wave:** 0
**Estimate:** M

## User Story

As a user viewing my Mox Amber (Schematic, smbro/98) in the collection,
I want to see the correct card image instead of a different card from the
base Brothers' War set.

## Problem

`src/utils/image_fallback.py` maps variant set code `smbro` to base `bro`
and constructs `https://api.scryfall.com/cards/bro/98?format=image` — but
BRO collector number 98 is a completely different card. The Schematic
printing uses a different numbering scheme than the base set.

This affects ALL variant set codes where the collector number doesn't
correspond to the base set's numbering (smbro, bldmr, blfdn, etc.).

## Dev Notes

### Root Cause
`fallback_image_uri()` remaps the set code but keeps the original collector
number. For variant sets, the CN in the variant set != CN in the base set.

### Fix Strategy

**Option A (recommended): Don't remap variant set codes in fallback**
The `_KNOWN_VARIANTS` mapping is designed for Scryfall API lookups where the
variant set code IS valid on Scryfall (e.g. Scryfall knows `smbro` as a
set). Instead of mapping to base set:
1. Use the ORIGINAL set code directly in the Scryfall API URL
2. Scryfall's `/cards/{set}/{cn}` endpoint accepts variant set codes

Test by checking: `https://api.scryfall.com/cards/smbro/98?format=image`
— if Scryfall recognizes `smbro` as a valid set, this returns the correct
Mox Amber Schematic image.

**Option B: Skip fallback for known variant prefixes**
If Scryfall doesn't recognize the variant code, return `None` from fallback
for variant set codes (let the frontend show a placeholder instead of a
wrong card).

### Files to Modify
- `src/utils/image_fallback.py` — stop remapping set code (use original)
- `tests/utils/test_image_fallback.py` — update expected URLs
- `tests/api/test_catalog_image_fallback.py` — update if affected

## Testing

- Verify `fallback_image_uri("smbro", "98")` returns URL with `smbro/98`
- Run: `pytest tests/utils/test_image_fallback.py tests/api/test_catalog_image_fallback.py --override-ini="addopts=" -q`
- Manual: check Mox Amber card in browser shows correct image
