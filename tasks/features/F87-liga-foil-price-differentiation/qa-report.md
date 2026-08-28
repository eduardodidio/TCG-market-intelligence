# F87 QA Report -- Liga Foil Price Differentiation

**QA Engineer:** QA Agent
**Date:** 2026-08-28
**Verdict:** PASS

---

## Test Results

| Suite | Result | Details |
|-------|--------|---------|
| Backend | 2644 passed, 0 failed | 41 warnings (all RuntimeWarning for unawaited coroutines in mocked tests -- pre-existing, unrelated) |
| Frontend | 1237 passed, 0 failed | 121 test files, all green |
| Foil-specific backend tests | 97 passed, 0 failed | Across 5 test files covering foil detection, price lookup, scan, refresh, and detail |

---

## Implementation Review

### src/collection/converter.py -- is_foil_entry()

Correct. Simple pure function: `"foil" in extras.lower()` with null/empty guard. Handles all reasonable variants (Foil, FOIL, "Foil, Signed", "Foil Etched"). 17 unit tests with parametrized edge cases in `tests/collection/test_is_foil_entry.py`.

### src/providers/liga/provider.py -- get_current_price(is_foil=...)

Correct. The `is_foil` keyword argument defaults to `False` (backward-compatible). When `is_foil=True`:
- Extracts from `prices["foil"]` dict (low -> mid -> high fallback)
- Returns `None` if no foil prices found (no silent fallback to normal -- correct)
- Suffixes external_id with `_foil`

### src/collectors/scan.py -- foil handling

Correct. Line 42 imports `is_foil_entry` from `converter.py` (the canonical source), aliased as `_is_foil`. The `_fetch_price_liga` function accepts `is_foil` parameter and constructs the correct external_id (`liga_{card_id}_foil` vs `liga_{card_id}`). The `process_entry` inner function calls `_is_foil(entry.get("extras"))` to determine foil status per entry.

### src/collectors/liga_sweep.py -- foil handling

Correct. Also imports from `converter.py` (line 32). The `_fetch_liga_price` function detects foil from the `extras` field and uses the `_foil` suffix.

### src/database/repository.py -- get_latest_prices_batch

Correct. The `foil_card_ids` parameter (optional, defaults to `None`) triggers foil-aware lookup:
- Queries `liga_{card_id}_foil` for foil cards
- When foil observation exists, removes normal Liga candidate from the list (prevents double-counting)
- Manual prices still win regardless of foil status (correct priority)
- Backward-compatible: `foil_card_ids=None` preserves existing behavior

8 dedicated integration tests in `tests/unit/database/test_repository_foil_prices.py` cover: foil gets foil price, non-foil gets normal price, manual beats foil, fallback when no foil obs exists, no observations returns None, backward compat, empty set same as None, foil replaces normal in candidates, mixed batch.

### src/database/repository.py -- get_cards_for_liga_scan (max_age_days)

Fixed. Lines 1384-1389 now check BOTH `liga_{card_id}` AND `liga_{card_id}_foil` against recent observations. This addresses the tech lead's finding #1 (MEDIUM bug). Foil cards will now be correctly skipped by the freshness filter when they have been recently scanned.

### src/database/repository.py -- get_collection_total_value

Correct. Handles foil/non-foil overlap: when the same `card_id` appears as both foil and non-foil entries, two separate calls to `get_latest_prices_batch` ensure each row gets the correct price variant.

### src/api/routers/collection.py -- list_collection and refresh endpoints

Correct. Uses `is_foil_entry` from `converter.py` throughout (finding #3 from tech lead was fixed -- line 1076 now uses the canonical function). The overlap handling for `list_collection` correctly dispatches to the right price dict per row.

### src/api/schemas/collection.py -- is_foil field

Correct. `is_foil: bool = False` -- computed server-side, non-optional, default False.

### frontend/src/components/FoilBadge.tsx

Clean. Two variants (compact/full), amber gradient styling, star SVG with `aria-hidden`, `data-testid="foil-badge"`, i18n via `t("card.foil")`. 9 tests in `tests/components/FoilBadge.test.tsx`.

### frontend/src/pages/MyCollection.tsx

Correct. Foil badge positioned at `bottom-2 left-2 z-10` on card tile image overlay. Only rendered when `card.is_foil` is true. Uses `data-testid="foil-badge-overlay"`.

### frontend/src/pages/CollectionCardDetail.tsx

Correct. Foil badge (full variant) placed inline next to card name. Price label switches between `t("cardDetail.latestPrice")` and `t("card.foilPrice")` based on `entry.is_foil`.

### frontend/src/types/api.ts

Correct. `is_foil: boolean` added to `CollectionCard` interface (non-optional, matches backend schema default).

### i18n Keys

Both locales have the required keys:
- `en.json`: `"foil": "Foil"`, `"foilPrice": "Foil price"` (under `card` namespace)
- `pt-BR.json`: `"foil": "Foil"`, `"foilPrice": "Preco Foil"` (under `card` namespace)

Dedicated i18n test file: `tests/i18n/foilKeys.test.ts` (4 tests, all pass).

---

## Tech Lead Findings Status

| # | Severity | Finding | Status |
|---|----------|---------|--------|
| 1 | MEDIUM | `get_cards_for_liga_scan` max_age_days only checks normal external_id | FIXED -- now checks both `liga_{card_id}` and `liga_{card_id}_foil` |
| 2 | LOW | `_is_foil()` duplicated in scan.py and liga_sweep.py | FIXED -- both now import from `converter.py` |
| 3 | LOW | Inline foil detection in collection.py line 1076 | FIXED -- now uses `is_foil_entry()` |
| 4 | LOW | Mock extras/is_foil inconsistency in test | FIXED -- mock now has `extras: "Foil"` with `is_foil: true` |

All four tech lead findings have been addressed.

---

## Test Coverage for Foil Scenarios

**Backend (18 files matching "foil"):**
- `tests/collection/test_is_foil_entry.py` -- 17 unit tests for the pure function
- `tests/unit/database/test_repository_foil_prices.py` -- 8 integration tests for price lookup
- `tests/collectors/test_scan_liga.py` -- foil handling in scan pipeline
- `tests/api/test_collection_refresh_liga.py` -- foil refresh endpoint
- `tests/api/test_collection_detail.py` -- foil display on detail endpoint
- `tests/fixtures/liga_card_foil_only.html` -- fixture for foil-only card

**Frontend (8 files matching "foil"):**
- `tests/components/FoilBadge.test.tsx` -- 9 tests for component rendering
- `tests/pages/CollectionCardDetail.test.tsx` -- foil badge on detail page
- `tests/pages/MyCollection.test.tsx` -- foil badge overlay on tiles
- `tests/i18n/foilKeys.test.ts` -- 4 i18n key tests
- `tests/pages/CollectionCardDetail.liga.test.tsx` -- Liga refresh with foil

---

## Gaps Found

None blocking. The implementation is complete and all tech lead findings have been resolved.

---

## Recommendations

1. **PT-BR accent on "Preco"**: The `card.foilPrice` key in `pt-BR.json` reads `"Preco Foil"` -- should be `"Preco Foil"` (with cedilla: `"Preco Foil"`). This is cosmetic and matches the project's existing pattern of omitting diacritics in JSON values, but worth noting for a future i18n cleanup pass.

2. **Etched foil distinction**: The current `is_foil_entry` treats "Foil Etched" as foil. If etched foil cards have different pricing on Liga (they sometimes do), a future feature could differentiate between regular foil and etched foil finishes.

3. **Dedicated `finish` column**: As noted in the F87 README risks section, the `extras` string parsing is fragile. Adding a dedicated `finish` enum column to `UserCollectionRow` would be more robust and is recommended for a future migration.
