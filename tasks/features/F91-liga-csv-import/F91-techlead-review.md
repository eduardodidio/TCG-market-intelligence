# F91 Liga CSV Import -- Tech Lead Review

**Reviewer:** Tech Lead Agent
**Date:** 2026-08-29
**Branch:** homol
**Verdict:** APPROVED with 2 required fixes (non-blocking)

---

## Summary

F91 adds Liga CSV import support to the collection importer: encoding auto-detection (UTF-8/cp1252), two new columns (`set_name_pt` from `Edicao (PTBR)`, `notes` from `Comentario`), set code normalization via `map_to_scryfall_set_code`, and a frontend CSV import modal on MyCollection. The implementation is clean, follows existing patterns, and test coverage is solid.

---

## Test Results

| Suite | Result |
|-------|--------|
| Backend (excl. pre-existing `test_seed_users` failure) | 622+ passed |
| Backend -- new tests (`test_importer_liga.py`) | 6/6 passed |
| Frontend | 1477 passed, 134 files, 0 failures |

The single backend failure (`tests/cli/test_seed_users.py::test_uses_default_password_when_no_env`) is pre-existing and unrelated to F91.

---

## Code Review

### Backend -- `src/collection/importer.py`

**Encoding detection** (`_detect_encoding`): Sound approach. Tries UTF-8 (with BOM support via `utf-8-sig`) first, falls back to `cp1252`. This correctly handles Liga's Windows-1252 exports. Reading the entire file into memory for detection is acceptable given CSV file sizes in this domain.

**New fields**: `set_name_pt` and `notes` are extracted from the correct Liga CSV column headers. Both use the standard `.strip() or None` pattern. Clean.

**Set code normalization**: Correctly applies `map_to_scryfall_set_code` on the raw set code before storage. This ensures Liga variant codes (like `smbro`) are normalized to Scryfall codes (`bro`) at import time.

**Auto-canonize**: The importer creates `CardRow` entries for unmatched cards and links them immediately. This is consistent with the existing import behavior.

### Backend -- `src/database/models.py`

Two new nullable columns on `UserCollectionRow`: `set_name_pt` (String 200) and `notes` (String 500). Both are nullable, which is correct for backward compatibility.

### Backend -- `src/api/schemas/collection.py`

`CollectionCard` schema correctly includes `set_name_pt: str | None = None` and `notes: str | None = None`. Backward-compatible defaults.

### Backend -- `src/api/routers/collection.py`

The `/import` endpoint uses `UploadFile`, writes to a temp file, calls the importer, and cleans up. Auth is enforced via `require_auth_or_api_key`. Background canonize task is scheduled. All good.

### Frontend -- `CsvImportModal.tsx`

Clean modal component following the project's established patterns (cf. `BatchAddModal`, `DeckImportModal`). Uses `data-testid` attributes for testing. State machine is clear (`idle -> uploading -> success/error`). Warning about collection replacement is prominent. Calls `onSuccess` on close after successful import (triggers refresh).

### Frontend -- `collection.ts` (`importCollectionCsv`)

Uses raw `fetch` with `FormData` -- necessary since `apiPost` sets `Content-Type: application/json`. Auth token is read from localStorage, consistent with other API calls.

### Frontend -- `MyCollection.tsx`

Import CSV button and modal are correctly wired. The `onSuccess` callback increments `refreshKey` to trigger a collection re-fetch.

### Frontend -- i18n

8 new keys in both `en.json` and `pt-BR.json`, all under `collection.*`. Keys are consistent between locales.

### Tests

- **Backend** (6 tests): encoding detection (UTF-8, Latin-1), new fields (`set_name_pt`, `notes`), set code normalization, encoding round-trip with accented characters. Good coverage.
- **Frontend** (9 tests): modal visibility, file input, upload states, success/error display, callback behavior, network error handling. Thorough.

---

## Issues Found

### REQUIRED FIX 1: Missing `_ensure_columns` migration for existing databases

**Severity:** High
**File:** `src/database/repository.py`

The two new columns (`set_name_pt`, `notes`) are added to the `UserCollectionRow` model, but `_ensure_columns()` does not include the corresponding `ALTER TABLE` statements. On the Render deployment (where the SQLite database already exists), `Base.metadata.create_all()` will NOT add columns to an existing table. Any query touching these columns will raise `OperationalError: no such column`.

**Fix:** Add migration logic to `_ensure_columns()`:

```python
if "user_collection" in insp.get_table_names():
    columns = {col["name"] for col in insp.get_columns("user_collection")}
    if "set_name_pt" not in columns:
        with self.engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE user_collection ADD COLUMN set_name_pt VARCHAR(200)"
            ))
    if "notes" not in columns:
        with self.engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE user_collection ADD COLUMN notes VARCHAR(500)"
            ))
```

### REQUIRED FIX 2: Frontend `CollectionCard` type missing new fields

**Severity:** Low
**File:** `frontend/src/types/api.ts`

The `CollectionCard` interface (line 110) does not include `set_name_pt` or `notes`, even though the backend schema returns them. While the frontend does not currently render these fields, the type should mirror the backend schema to prevent runtime surprises and support future use.

**Fix:** Add to the `CollectionCard` interface:

```typescript
export interface CollectionCard {
  // ... existing fields ...
  set_name_en: string | null;
  set_name_pt: string | null;  // <-- add
  notes: string | null;         // <-- add
  quantity: number;
  // ...
}
```

---

## Minor Observations (non-blocking)

1. **`importCollectionCsv` does not check `res.ok`**: If the server returns a non-200 status (e.g., 401, 500), `res.json()` may fail or return unexpected data. The modal's `try/catch` handles this gracefully by showing a generic error, so this is acceptable but could be improved with explicit status checking.

2. **No file size limit on upload**: The endpoint accepts arbitrarily large CSV files. For a single-user deployment this is fine, but consider adding a size check (e.g., 10MB) in a future hardening pass.

3. **Collection replacement warning**: The warning text says "This will replace your entire collection" which is accurate (the importer deletes existing rows before inserting). This is a destructive operation -- consider adding a confirmation step in a future UX pass.

---

## Architecture Assessment

The feature integrates cleanly with the existing codebase:
- Encoding detection is a focused, testable utility function
- Set code normalization reuses the existing `map_to_scryfall_set_code` utility
- The modal follows established component patterns
- Auth is properly enforced on the import endpoint
- Schema changes are backward-compatible (nullable columns with defaults)

No architectural concerns.

---

## Verdict

**APPROVED** -- Ship after applying the two required fixes:
1. Add `_ensure_columns` migration for `set_name_pt` and `notes` on `user_collection`
2. Add `set_name_pt` and `notes` to the frontend `CollectionCard` type

Both fixes are straightforward and can be done in the same commit.
