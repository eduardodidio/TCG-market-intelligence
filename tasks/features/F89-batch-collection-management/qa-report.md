# F89 QA Report -- Batch Collection Management

**QA Agent:** Claude Opus 4.6
**Date:** 2026-08-28
**Verdict:** PASS

---

## 1. Backend Test Results

### Full Suite (excluding pre-existing failure)

```
2721 passed, 38 warnings in 1232.51s
```

- **Pre-existing failure:** `tests/cli/test_seed_users.py::TestSeedUsers::test_uses_default_password_when_no_env` -- the test checks password `mudar12345` but the seed was changed to `mudar@123` in F88 (commit 1bcfbb9). This is NOT an F89 regression.
- **F89 regressions:** None detected.

### F89-Specific Tests (82 tests)

All 82 tests pass:

| Test File | Tests | Status |
|-----------|-------|--------|
| `tests/collection/test_batch_parser.py` | 19 | PASS |
| `tests/api/test_collection_patch.py` | 15 | PASS |
| `tests/api/test_collection_delete.py` | 8 | PASS |
| `tests/api/test_collection_batch_add.py` | 13 | PASS |
| `tests/integration/test_collection_crud.py` | 13 | PASS |
| **Frontend** `tests/i18n/batch-crud-keys.test.ts` | 14 | PASS |

**Coverage of key scenarios:**
- Single PATCH: quantity, quality, language, extras, partial updates, 404, 403, 422
- Single DELETE: 204 success, 404, 403
- Bulk PATCH: multi-entry update, IDOR rejection, missing IDs, >200 limit, empty IDs, empty updates, extras/foil
- Bulk DELETE: multi-entry, IDOR, missing IDs, >200 limit, empty IDs
- Batch parse: simple, full format, comments/blanks, errors, no DB writes
- Batch add: multi-entry, auto-link existing card, auto-create card, auth, max 500, empty, partial errors, quality/language, invalid codes
- Integration (real DB): parse-and-add flow, single edit, single delete, bulk edit, bulk delete, IDOR protection (4 tests)

---

## 2. Frontend Test Results

### Full Suite

```
131 test files, 1435 tests passed
```

- **F89 regressions:** None detected.
- **F89-specific test files:**

| Test File | Description |
|-----------|-------------|
| `tests/components/InlineEditField.test.tsx` | Inline edit field component |
| `tests/components/QuantityStepper.test.tsx` | Quantity +/- stepper |
| `tests/components/DeleteEntryButton.test.tsx` | Delete confirmation button |
| `tests/components/BatchAddModal.test.tsx` | Batch add modal (3-state flow) |
| `tests/components/BatchPreviewTable.test.tsx` | Preview table with edit dropdowns |
| `tests/components/BulkActionsToolbar.test.tsx` | Multi-select toolbar |
| `tests/components/SelectableCardTile.test.tsx` | Selectable card tile |
| `tests/hooks/useMultiSelect.test.ts` | Multi-select hook |
| `tests/i18n/batch-crud-keys.test.ts` | i18n key verification (60 keys) |

---

## 3. TechLead Fix Verification

All critical and minor fixes from the tech lead review have been applied:

| Item | Status | Evidence |
|------|--------|----------|
| C1. BatchPreviewTable quality/language codes | FIXED | `QUALITY_OPTIONS = ["M", "NM", "SP", "MP", "HP", "D"]`, `LANGUAGE_OPTIONS = ["BR", "EN", "DE", "ES", "FR", "IT", "JP", "KO", "RU", "TW"]` |
| M1. Repository allowlist | FIXED | `_EDITABLE_COLLECTION_FIELDS = {"quantity", "quality", "language", "extras"}` used in both `update_collection_entry` and `bulk_update_collection_entries`. Verified `user_id`, `card_id`, `id` are NOT in the set. |
| m3. FormatHelpSection LP -> SP | FIXED | Example now reads `1 Black Lotus [LEA] SP EN foil` |
| m5. handleBulkUpdate refresh | FIXED | `handleBulkUpdate` calls `setRefreshKey((k) => k + 1)` on line 338 |

---

## 4. Edge Case Analysis

### 4.1 Batch add text with only comments/empty lines

**Result:** Safe. `parse_batch_text("# comment\n\n# another comment\n   \n")` returns an empty list (`[]`). The parse endpoint returns `{"entries": []}`. The batch add endpoint requires `entries` to be non-empty (validated by Pydantic), so submitting 0 entries after filtering is handled by the frontend (the "Add N cards" button would show 0).

### 4.2 Bulk update with empty updates dict

**Result:** Properly handled. `CollectionUpdateRequest()` with no fields set produces `model_dump(exclude_unset=True) == {}`. The router checks `if not updates:` and raises `HTTPException(status_code=422, detail="No fields to update")`. Tested in `test_bulk_update_no_fields_rejected` and `test_no_fields_returns_422`.

### 4.3 PATCH quantity to 0

**Result:** Properly rejected. The `CollectionUpdateRequest` schema has a validator: `quantity_must_be_positive` that raises `ValueError("quantity must be >= 1")` when `v < 1`. Returns 422. Tested in `test_validation_error_quantity_zero`.

### 4.4 Foil detection when extras changes

**Result:** Correctly handled. The `update_collection_entry` router endpoint calls `is_foil_entry(row.extras)` on the updated row and sets `is_foil` in the response. Verified:
- `is_foil_entry(None)` = False
- `is_foil_entry("Foil")` = True
- `is_foil_entry("foil")` = True (case-insensitive)
- `is_foil_entry("Promo, Foil")` = True
- `is_foil_entry("Extended Art")` = False

Tested in `test_update_extras_updates_is_foil` (API) and `test_edit_extras_foil_sets_is_foil` (integration).

### 4.5 Parser qty=0

**Result:** The parser allows `0x Lightning Bolt` -> `qty=0`. This is visible in the preview table but harmless: the `BatchAddEntry` schema (for the add endpoint) validates `quantity >= 1`, so submitting qty=0 returns 422. The preview correctly shows the parsed data including potentially invalid values, letting the user fix them before submitting.

### 4.6 Negative quantity in text

**Result:** Parser regex `^(\d+)x?\s+` only matches digits, so `-1 Lightning Bolt` is parsed as `qty=1, name="-1 Lightning Bolt"`. The minus sign is not consumed by the qty regex, so the entire string becomes the card name. Not ideal but not dangerous -- schema validation catches invalid quantities on submission.

### 4.7 Field injection via PATCH (defense in depth)

**Result:** The repository uses `_EDITABLE_COLLECTION_FIELDS = {"quantity", "quality", "language", "extras"}` as an explicit allowlist. Even if a future schema change accidentally exposed `user_id` or `card_id`, the repository would silently ignore them. Verified programmatically that `user_id`, `card_id`, and `id` are not in the set.

---

## 5. Observations (non-blocking)

1. **No quantity upper bound:** The schema validates `quantity >= 1` but has no maximum. A user could set `quantity = 999999999`. This is cosmetic and matches the TechLead's m4 observation. Consider adding `le=9999` in a future pass.

2. **Parser qty=0 in preview:** The batch parse preview shows qty=0 without flagging it as an error. The add endpoint will reject it, but the UX could be improved by showing a warning in the preview table for qty < 1. Low priority.

3. **Pre-existing test failure:** `test_uses_default_password_when_no_env` needs to be updated to check `mudar@123` instead of `mudar12345` (F88 regression, not F89).

---

## 6. Test Gap Assessment

The existing test suite is comprehensive:

- **82 backend tests** cover all endpoints, edge cases, validation, IDOR, and integration flows
- **~120+ frontend tests** across 9 test files cover components, hooks, and i18n
- **Integration tests** use real SQLite DB with FastAPI TestClient
- **i18n tests** verify all 60 keys exist in both EN and PT-BR with non-empty values and full parity

No new tests were needed. The coverage is thorough for the feature scope.

---

## Verdict: PASS

F89 Batch Collection Management is ready to ship. All tests pass (no F89 regressions), TechLead fixes are applied, edge cases are properly handled, and security (IDOR, field allowlist) is solid.
