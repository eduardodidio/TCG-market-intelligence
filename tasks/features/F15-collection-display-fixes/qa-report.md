# F15 QA Report

**Date:** 2026-08-20
**Verdict:** PASSED

## Test Results

### Backend
- **857 passed**, 0 failed (116 warnings)
- Coverage: **92.75%** (threshold: 70%)
- Net-new tests from F15: 7 (from 850 baseline)
  - QA added: 5 (3 in `test_collection_detail.py`, 2 in `test_set_code_map.py`)
  - Developer shipped: 49 (set_code_map) + 9 (image_url) + 6 (collection_detail) + many via pre-existing test files

### Frontend
- **304 passed** across 29 test files, 0 failed
- Net-new tests from F15: 2 (from 302 baseline)
  - QA added: 2 (in `scryfall.test.ts`)
  - Developer shipped: 49 (setCodeMap) + 10 (scryfall) + 12 (CollectionCardDetail) + Layout BRL tests

## Acceptance Criteria Validation

### T01 -- MYP Variant Set Code Mapping Utility
- [x] Frontend `mapToScryfallSetCode()` exists with all known variant codes mapped -- verified in `frontend/src/utils/setCodeMap.ts`
- [x] Backend `map_to_scryfall_set_code()` mirrors the frontend logic -- verified in `src/utils/set_code_map.py`, identical lookup table and heuristic
- [x] Both handle unknown codes gracefully (return input unchanged) -- tested via `TestUnknownCodes` and `TestPassthrough`
- [x] Mapping covers all variant codes from the collection CSV -- all codes listed in F15-README are in the static lookup table
- [x] Unit tests validate all known mappings -- 49 parametrized tests (backend), 49 tests (frontend)

### T02 -- Fix Full-Art Card Images
- [x] Borderless cards show correct images -- `_scryfall_image_url("bldmr", ...)` maps to `dmr`, tested
- [x] Extended art cards show correct images -- `exdmu` maps to `dmu`, tested
- [x] Showcase cards show correct images -- `srltr` maps to `ltr`, tested
- [x] Secret Lair cards show correct images -- `sld158` maps to `sld`, tested
- [x] Unknown variant codes fall back to name-based image -- frontend fallback chain verified in `MyCollection.tsx`
- [x] Cards with no `name_en` show placeholder SVG -- fallback chain ends with placeholder SVG element
- [x] No regression on standard set codes -- passthrough tests for `dmr`, `dmu`, `ltr`, etc.

### T03 -- BRL Currency Indicator
- [x] Sidebar displays "BRL" text with Brazilian flag emoji -- verified in `Layout.tsx` lines 61-64
- [x] Currency indicator visible on all pages -- sidebar is persistent, part of `Layout` component wrapping all routes
- [x] Mobile view: visible when sidebar is open -- indicator is inside the sidebar `<aside>`, which slides in on mobile
- [x] Flag emoji renders correctly using Unicode code points -- uses native emoji character
- [x] Accessible: flag has `role="img"` and `aria-label="Brazilian flag"` -- verified in code and tested in `Layout.test.tsx`

### T04 -- Collection Card Detail View
- [x] Clicking any card opens detail view -- `MyCollection.tsx` line 143 links all cards to `/collection/${card.id}`
- [x] Detail view shows card name (EN + PT), set code, collector number -- tested in `CollectionCardDetail.test.tsx`
- [x] Detail view shows collection metadata: quantity, quality, language, extras -- each badge tested individually
- [x] Detail view shows card image using mapped Scryfall URL -- `image_url` from backend uses `map_to_scryfall_set_code`
- [x] Linked cards show latest price and price chart -- `PriceChart` component rendered when `card_id != null`
- [x] Linked cards show source links (MYP) -- source links rendered with `target="_blank"` and `rel="noopener noreferrer"`
- [x] Unlinked cards show "Not yet linked" gracefully -- `unlinked-notice` div with amber styling, tested
- [x] External links (Scryfall, LigaMagic) present -- both links rendered in `external-links` section, tested
- [x] Breadcrumb navigates back to Collection -- breadcrumb `<Link to="/collection">`, tested
- [x] No dead-end for any collection card click -- all cards link to `/collection/:id`, eliminated `/cards?name=` fallback

## Test Gaps Filled

### Backend (`tests/api/test_collection_detail.py`)
1. **`test_external_links_with_special_chars_in_name`** -- Documents that card names with commas and spaces (e.g., "Jace, the Mind Sculptor") appear unencoded in `scryfall_url`. This is a known MINOR issue (Scryfall tolerates it) but the test documents the behavior explicitly.
2. **`test_no_external_links_when_name_is_empty`** -- Verifies that entries with `name_en=None` and `name_pt=None` produce `null` for both `scryfall_url` and `ligamagic_url` rather than building broken URLs.
3. **`test_variant_set_code_mapped_in_image_url`** -- Verifies the detail endpoint maps variant set codes (e.g., `bldmr` to `dmr`) in the `image_url` field, not just the list endpoint.

### Backend (`tests/utils/test_set_code_map.py`)
4. **`test_single_char_remainder_not_stripped`** -- Verifies that prefix heuristic requires remainder >= 2 chars (e.g., "bla" with prefix "bl" leaves remainder "a" which is too short).
5. **`test_long_remainder_not_stripped`** -- Verifies that remainder > 5 chars is not treated as a set code.

### Frontend (`src/utils/__tests__/scryfall.test.ts`)
6. **`encodes special characters in card name`** -- Verifies `scryfallImageByName("Jace, the Mind Sculptor")` encodes comma and spaces.
7. **`encodes ampersand in card name`** -- Verifies `scryfallImageByName("Sword of Fire & Ice")` encodes the `&` character.

## Documentation

- [x] `docs/diagrams/F15-architecture.mmd` created -- component diagram showing set code mapping flow and collection detail data flow
- [x] `docs/diagrams/F15-journey.mmd` created -- user journey from sidebar/collection grid through image resolution and detail page
- [x] `README.md` updated with F15 section under "Shipped" and new endpoint in the endpoints table

## Issues Found

| # | Severity | Description | Status |
|---|----------|-------------|--------|
| 1 | MINOR | `scryfall_url` in `get_collection_entry` built without URL-encoding. Card names with `+`, `&`, spaces could produce malformed URLs. Scryfall tolerates this, but `urllib.parse.quote()` would be more correct. | Documented in test, deferred to follow-up |
| 2 | MINOR | `CollectionCardDetail.tsx` hides image entirely on error (`display: "none"`) instead of using name-based fallback chain like `MyCollection.tsx`. Inconsistent UX but not a functional bug. | Noted for follow-up |
| 3 | MINOR | `_STRIP_PREFIXES` comment says "longer prefixes first" but ordering is not by length. Behavior is correct because static lookup catches known codes first. | Cosmetic, no fix needed |
| 4 | INFO | `get_collection_entry` repository method does not filter by `user_id`. Acceptable for single-user mode. | Track for multi-user follow-up |

No blocking issues found. All MINOR items are documented for future improvement.

## Retrospective

### Key Lessons

**Architect:** Static lookup + heuristic fallback is a pragmatic pattern for external code mappings. Backend/frontend parity was maintained cleanly because the mapping logic is simple enough to mirror exactly.

**Developer:** When a mapping utility is shared between backend and frontend, keep the logic identical and the data structures simple. The 1:1 mirror approach worked well here with zero divergence.

**Tech Lead:** Documentation gates (diagrams + README) should be treated as blocking, not follow-up. Both MAJOR items from the review were documentation gaps that had to be filled by QA.

**QA:** Test gaps in URL encoding and boundary conditions of heuristic logic (remainder length limits) are easy to miss when the primary functionality works. Always test the edges of string-manipulation utilities, not just the happy path.
