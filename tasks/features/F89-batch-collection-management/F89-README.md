# F89 — Batch Collection Management

**Status:** planned
**Created:** 2026-08-28
**Description:** LigaMagic-style batch add, batch edit, single card edit, and delete for collection entries.

## Summary

Add full CRUD capabilities to the collection beyond CSV import. Users can add cards via text paste (LigaMagic format), edit metadata inline (single or bulk), and delete entries — all with auth, IDOR protection, and i18n.

## Tasks

| Task | Title | Wave | Depends |
|------|-------|------|---------|
| T01 | Backend: PATCH/DELETE collection endpoints | 0 | — |
| T02 | Backend: Batch add parser + POST endpoint | 0 | — |
| T03 | Frontend: Single card inline edit | 1 | T01 |
| T04 | Frontend: Batch add modal (text paste + preview) | 1 | T02 |
| T05 | Frontend: Multi-select + bulk actions toolbar | 1 | T01 |
| T06 | i18n keys + integration tests | 2 | T03, T04, T05 |

## Wave Plan

- **Wave 0** (T01, T02): Backend endpoints — fully parallel, no frontend dependency
- **Wave 1** (T03, T04, T05): Frontend components — fully parallel, each depends only on its backend task from Wave 0
- **Wave 2** (T06): i18n completion + integration tests across all features

## Architecture Notes

- No DB migration needed — `UserCollectionRow` already has qty, quality, language, extras fields
- PATCH endpoint: accepts partial updates `{quantity?, quality?, language?, extras?}`
- Bulk PATCH: `PATCH /collection/bulk` with `{ids: [...], updates: {...}}`
- Bulk DELETE: `DELETE /collection/bulk` with `{ids: [...]}`
- Batch add: `POST /collection/batch` with `{entries: [{name_en, set_code?, collector_number?, quantity?, quality?, language?, extras?}, ...]}`
- Text parser: `"2 Lightning Bolt [m15] NM EN Foil"` → structured entry
- All endpoints require JWT auth + user_id scoping (IDOR protection)
- Changing extras affects `is_foil_entry()` → price lookup strategy changes accordingly
