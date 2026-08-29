# F91 — Liga CSV Import

**Status:** planned
**Created:** 2026-08-29

## Summary

Enhance the collection CSV importer to fully support LigaMagic CSV exports:
auto-detect encoding (UTF-8/Latin-1/CP-1252), import two missing columns
(`Edicao (PTBR)` as `set_name_pt`, `Comentario` as `notes`), normalize Liga
variant set codes via existing `map_to_scryfall_set_code`, and add a frontend
CSV import UI on the MyCollection page.

## Context

The Liga CSV export format has identical column headers to what the current
importer already reads. However three gaps exist:

1. **Encoding**: Liga exports in CP-1252/Latin-1, not UTF-8. Accented
   characters (e.g. "Irmãos") become mojibake (`Irm�os`) with current
   `utf-8` + `errors="replace"`.
2. **Missing fields**: `Edicao (PTBR)` and `Comentario` columns are silently
   ignored — no storage columns exist.
3. **Set code variants**: Liga uses variant codes like `smbro`, `cbafr`,
   `pl24` that are not normalized to Scryfall codes during import.
4. **No frontend import**: CSV import only via CLI/API — no UI.

## Tasks

| Task | Description | Wave |
|------|-------------|------|
| T01  | Schema: add `set_name_pt` + `notes` to UserCollectionRow | 0 |
| T02  | Backend: encoding auto-detect + new fields + set code normalization | 1 |
| T03  | Frontend: CSV import modal on MyCollection page | 1 |

## Waves

- **Wave 0** (T01): Schema change — prerequisite for all other work
- **Wave 1** (T02 + T03): Backend importer enhancement + frontend UI — parallel

## Architecture Notes

- No new dependencies. Encoding detection uses try-UTF-8-first heuristic.
- `map_to_scryfall_set_code` already handles Liga variant codes.
- Frontend reuses existing `POST /collection/import` endpoint.
- The import is destructive (clears + re-imports) — existing behavior preserved.
