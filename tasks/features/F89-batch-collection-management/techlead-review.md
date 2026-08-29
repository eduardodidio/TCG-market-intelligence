# F89 Tech Lead Review -- Batch Collection Management

**Reviewer:** Tech Lead
**Date:** 2026-08-28
**Verdict:** APPROVED (with mandatory fixes for Critical #1)

---

## Summary

F89 delivers full CRUD for collection entries: single PATCH/DELETE, bulk PATCH/DELETE, batch text-paste add with preview, and multi-select UI. The architecture is clean, endpoints are RESTful, auth/IDOR protection is consistent, and the pure-function parser is well designed. One critical bug and a few minor issues need attention before shipping.

---

## Critical Findings

### C1. Quality and Language code mismatch between frontend preview table and backend validation

**Files:** `frontend/src/components/BatchPreviewTable.tsx` (lines 21-22) vs `src/api/schemas/collection.py` (lines 155-156)

The `BatchPreviewTable` defines:
```typescript
const QUALITY_OPTIONS = ["NM", "LP", "MP", "HP", "DMG"];
const LANGUAGE_OPTIONS = ["EN", "PT", "ES", "FR", "DE", "IT", "JP", "KR", "CN", "RU"];
```

The backend `VALID_QUALITY_CODES` and `VALID_LANGUAGE_CODES` are:
```python
VALID_QUALITY_CODES = {"M", "NM", "SP", "MP", "HP", "D"}
VALID_LANGUAGE_CODES = {"BR", "EN", "DE", "ES", "FR", "IT", "JP", "KO", "RU", "TW"}
```

Differences:
- **Quality:** Frontend has `LP`, `DMG` -- backend rejects both. Backend has `M`, `SP`, `D` -- frontend never offers them.
- **Language:** Frontend has `PT`, `KR`, `CN` -- backend rejects all three. Backend has `BR`, `KO`, `TW` -- frontend never offers them.

A user selecting `LP` quality or `PT` language in the preview table will get a 422 validation error on submit. The `BulkActionsToolbar` (line 4-5) correctly uses the backend codes (`M/NM/SP/MP/HP/D` and `BR/EN/...`), so only `BatchPreviewTable` is wrong.

**Fix:** Align `BatchPreviewTable` constants with backend codes. This is the same set already used in `BulkActionsToolbar` and the parser (`batch_parser.py`).

---

## Major Findings

### M1. Repository `update_collection_entry` uses `hasattr` for field whitelisting

**File:** `src/database/repository.py` (lines 926-928, 981-983)

```python
for key, value in updates.items():
    if hasattr(row, key):
        setattr(row, key, value)
```

The `hasattr` check means any attribute on `UserCollectionRow` can be set -- including `user_id`, `card_id`, or `id`. While Pydantic's `CollectionUpdateRequest` schema currently limits input to `quantity/quality/language/extras`, this is defense-in-depth: if someone later adds a field to the schema without realizing the repo accepts anything, it becomes a privilege escalation vector.

**Recommendation:** Add an explicit allowlist in the repo method:

```python
ALLOWED_UPDATE_FIELDS = {"quantity", "quality", "language", "extras"}
for key, value in updates.items():
    if key in ALLOWED_UPDATE_FIELDS:
        setattr(row, key, value)
```

This applies to both `update_collection_entry` and `bulk_update_collection_entries`.

### M2. Batch add creates duplicate CardRow entries on repeated imports

**File:** `src/collection/batch_add.py` (lines 123-132)

When `_resolve_card` cannot match by `set_code + collector_number`, it creates a new `CardRow`. If the user batch-adds "Lightning Bolt" (no set code) three times across three operations, three separate `CardRow` entries are created with `set_code=None`. This is consistent with the existing CSV importer pattern (noted in the module docstring), but worth flagging: over time the `cards` table accumulates orphan minimal-CardRow entries.

**Recommendation:** Consider matching by `name_en` as a fallback when `set_code` is absent, or document this as known behavior. Not blocking -- same pattern as existing importer.

---

## Minor Findings

### m1. `batch_add` endpoint does double-commit

**File:** `src/api/routers/collection.py` (lines 1361-1367)

The `batch_add_entries` function calls `session.flush()` per entry (line 84 of `batch_add.py`), then the router calls `session.commit()`. This is correct -- flush writes to DB without committing, and the final commit is atomic. However, `batch_add_entries` also uses `session.begin_nested()` (savepoints) for per-entry error isolation. If one entry fails, the savepoint rolls back but other entries proceed. The outer `session.commit()` then commits only the successful entries. This is good design.

No action needed -- just confirming the pattern is sound.

### m2. `POST /collection/bulk-delete` instead of `DELETE /collection/bulk`

**File:** `src/api/routers/collection.py` (line 410)

The docstring correctly explains why: `DELETE` with a request body is non-standard per HTTP spec. Using `POST` is the pragmatic choice and matches industry conventions (e.g., GitHub API). Good call.

### m3. FormatHelpSection example shows `LP` quality code

**File:** `frontend/src/components/FormatHelpSection.tsx` (line 38)

The example shows `1 Black Lotus [LEA] LP EN foil`. The backend parser (`batch_parser.py`) will not recognize `LP` as a quality code -- it only knows `{M, NM, SP, MP, HP, D}`. The `LP` will remain part of the card name, resulting in `"Black Lotus LP"` as the parsed name.

**Fix:** Change the example to use a valid quality code (e.g., `SP`).

### m4. No upper bound on quantity in repo methods

The Pydantic schemas validate `quantity >= 1` but have no upper bound. A user could set `quantity = 999999999`. This is cosmetic but worth adding a reasonable cap (e.g., 9999) in the schema validator.

### m5. `handleBulkUpdate` in MyCollection does not refresh on success

**File:** `frontend/src/pages/MyCollection.tsx` (lines 331-339)

After a successful bulk update, `handleBulkDelete` correctly calls `setRefreshKey` to re-fetch (line 348-ish), but `handleBulkUpdate` does not appear to trigger a re-fetch. The user would see stale quality/language values until they manually refresh. Verify and add `setRefreshKey(k => k + 1)` after successful bulk update.

---

## Architecture Assessment

**Positive observations:**

1. **Clean separation of concerns.** The parser is a pure function with no I/O. The batch_add orchestrator takes a Session and is testable. The router is thin glue.

2. **IDOR protection is thorough.** Every mutating endpoint checks `user_id` ownership. Both single and bulk operations verify ownership before any mutation. The bulk operations check ALL entries belong to the user before applying ANY updates (atomic all-or-nothing).

3. **Consistent error handling.** ValueError from repo -> 403/404 in router. Pydantic handles input validation with clear error messages.

4. **Good use of savepoints.** The batch add uses `begin_nested()` for per-entry error isolation without losing successful entries.

5. **Frontend UX is well thought out.** The 3-state modal (input -> preview -> result), inline editing with keyboard shortcuts (Enter/Escape), multi-select with fixed toolbar -- all follow established patterns.

6. **i18n coverage.** All user-facing strings go through `t()`. The 60 new keys cover both languages.

**Schema design is RESTful:**
- `PATCH /collection/{id}` -- partial update (correct use of PATCH)
- `DELETE /collection/{id}` -- single delete with 204 No Content
- `PATCH /collection/bulk` -- bulk update
- `POST /collection/bulk-delete` -- bulk delete (POST over DELETE for body support)
- `POST /collection/batch/parse` -- preview (no side effects)
- `POST /collection/batch` -- batch create

---

## Test Assessment

- 82 backend tests + 198 frontend tests is strong coverage for this feature scope.
- The batch parser being a pure function makes it highly testable.
- Integration tests for IDOR on bulk operations are important -- verify they exist.

---

## Action Items

| Priority | Item | Owner |
|----------|------|-------|
| CRITICAL | Fix BatchPreviewTable quality/language codes to match backend | Developer |
| Major | Add allowlist in repo update methods (defense-in-depth) | Developer |
| Minor | Fix FormatHelpSection example (`LP` -> `SP`) | Developer |
| Minor | Verify `handleBulkUpdate` triggers re-fetch after success | Developer |
| Optional | Add quantity upper bound (9999) in schema | Developer |

---

**Verdict: APPROVED** -- the architecture is solid, security is well handled, and code quality is high. The critical BatchPreviewTable code mismatch must be fixed before merge as it will cause runtime 422 errors for users editing quality/language in the preview table.
