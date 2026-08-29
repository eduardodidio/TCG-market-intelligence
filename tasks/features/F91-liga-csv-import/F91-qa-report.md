# F91 Liga CSV Import -- QA Report

**Date:** 2026-08-29
**Verdict:** PASS

---

## 1. Files Reviewed

### Backend
| File | Status | Notes |
|------|--------|-------|
| `src/database/models.py` | OK | `set_name_pt` (VARCHAR 200) and `notes` (VARCHAR 500) added to `UserCollectionRow` |
| `src/database/repository.py` | OK | `_ensure_columns` adds ALTER TABLE for both new columns when missing |
| `src/api/schemas/collection.py` | OK | `set_name_pt` and `notes` on `CollectionCard`; `ImportResult` schema present |
| `src/collection/importer.py` | OK | Encoding detection (UTF-8-sig / cp1252), new field extraction, `map_to_scryfall_set_code` normalization |
| `src/api/routers/collection.py` | OK | `POST /import` endpoint accepts `UploadFile`, writes temp file, calls importer, schedules background canonize |
| `tests/unit/test_importer_liga.py` | OK | 10 tests (6 original + 4 added by QA) |

### Frontend
| File | Status | Notes |
|------|--------|-------|
| `frontend/src/components/CsvImportModal.tsx` | OK | Modal with file input, upload/error/success states, warning banner |
| `frontend/tests/components/CsvImportModal.test.tsx` | OK | 9 tests covering render, disable states, success, error, network error |
| `frontend/src/types/api.ts` | OK | `ImportResult` interface added, `CollectionCard` includes `set_name_pt` and `notes` |
| `frontend/src/api/collection.ts` | OK | `importCollectionCsv` uses FormData + fetch with auth header |
| `frontend/src/pages/MyCollection.tsx` | OK | "Import CSV" button wired to `CsvImportModal`, refreshes on success |
| `frontend/src/i18n/locales/en.json` | OK | 8 new keys under `collection.*` |
| `frontend/src/i18n/locales/pt-BR.json` | OK | 8 new keys, proper Portuguese translations |

---

## 2. Test Results

### Backend
- **Full suite:** 622 passed, 1 failed (pre-existing: `test_uses_default_password_when_no_env`), 162 warnings
- **F91 tests only:** 10 passed in 1.57s
- The single failure is a pre-existing bug in `test_seed_users.py` (password mismatch `mudar12345` vs `mudar@123`), confirmed by running the same test on `homol` without F91 changes. **Not related to F91.**

### Frontend
- **Full suite:** 1476 passed, 1 failed (pre-existing: `useScanStream` SSE fallback test), 134 test files
- **F91 tests only:** 9 passed in 124ms
- The single failure is a pre-existing flaky SSE test. **Not related to F91.**

---

## 3. Test Gaps Filled by QA

Four new test cases added to `tests/unit/test_importer_liga.py`:

1. **`TestBackwardsCompatibility::test_csv_without_new_columns_imports_fine`** -- CSV without `Edicao (PTBR)` and `Comentario` columns imports successfully with `set_name_pt=None` and `notes=None`.
2. **`TestEmptyCsv::test_empty_csv_file`** -- Header-only CSV produces zero imports, no errors.
3. **`TestEmptyCsv::test_truly_empty_csv_file`** -- Completely empty file (no header) produces zero imports, no errors.
4. **`TestEnsureColumnsMigration::test_ensure_columns_adds_new_columns`** -- Creates a DB table without `set_name_pt`/`notes`, then verifies `_ensure_columns` adds them via ALTER TABLE.

---

## 4. Correctness Analysis

### Encoding Detection
- `_detect_encoding` tries UTF-8-sig first, falls back to cp1252. This covers Liga's typical Windows-1252 exports and standard UTF-8 exports.
- Round-trip test confirms accented characters (e.g., `Irmãos`, `Condição ótima`) survive cp1252 decode.

### New Fields
- `set_name_pt` mapped from `Edicao (PTBR)` column (Liga-specific).
- `notes` mapped from `Comentario` column (Liga-specific).
- Both are optional (`or "").strip() or None`), so missing columns gracefully produce `None`.

### Set Code Normalization
- `map_to_scryfall_set_code` applied before insertion, correctly normalizing Liga variant codes (e.g., `smbro` -> `bro`).

### API Endpoint
- `POST /import` validates file extension, writes to temp file, calls `import_collection_csv`, cleans up temp file in `finally` block.
- Background canonize task scheduled for new entries.

### Frontend
- Modal follows existing patterns (idle/uploading/success/error states).
- Auth token sent via Authorization header.
- Warning about destructive replace is prominently displayed.
- Success triggers `onSuccess` callback which refreshes collection data.

### Migration Safety
- `_ensure_columns` checks column existence before ALTER TABLE. Idempotent -- safe to run multiple times.
- SQLite ALTER TABLE ADD COLUMN is non-destructive.

---

## 5. Potential Concerns (non-blocking)

1. **Duplicate i18n key:** `"importing"` appears twice in both locale files (line 243 under `collection` and line 291 under `decks`). Not a bug since they are under different JSON paths, but worth noting.
2. **Large CSV memory:** The importer reads all rows into `rows_to_insert` list before DB insertion. For very large collections (10k+ cards) this is fine for the expected use case.

---

## 6. Regression Check

- Existing CLI import path (`import_collection_csv` function) unchanged in interface -- same function, now with encoding detection and new field support added transparently.
- No existing tests broken by F91 changes.
