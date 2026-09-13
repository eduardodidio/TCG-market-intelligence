# F124 — Liga URL Definitive Fix

**Status:** planned
**Priority:** high
**Waves:** 2

## Problem

Liga Magic links are broken in multiple places:

1. **Split/DFC cards** — Names like "Painter's Studio // Defaced Gallery" are sent whole to Liga, which only recognizes the front face name
2. **CardDetail.tsx** — Builds Liga URL in frontend using `encodeURIComponent` (not `quote_plus`), missing `&show=1`
3. **card_search.py** — Liga URL missing `&show=1` parameter
4. **No centralized URL building** — 3 different places build Liga URLs with inconsistent formats

## Solution

1. Centralize Liga URL generation in a single backend utility (`liga_url_for_card_name`)
2. Handle split/DFC card names by stripping the back face (`name.split(" // ")[0]`)
3. Add `ligamagic_url` field to the `CardDetail` API schema/response
4. Fix `card_search.py` to include `&show=1`
5. Remove hardcoded URL construction from `CardDetail.tsx`
6. Comprehensive test coverage for all card name variants

## Tasks

| Task | Description | Wave |
|------|-------------|------|
| T01 | Centralize Liga URL utility + fix split/DFC names | 0 |
| T02 | Add `ligamagic_url` to CardDetail API + fix card_search.py + fix CardDetail.tsx | 0 |
| T03 | Comprehensive Liga URL test coverage (card-by-card) | 1 |

## Wave Layout

- **Wave 0**: T01, T02 (T02 depends on T01's utility function, run sequentially)
- **Wave 1**: T03 (tests)
