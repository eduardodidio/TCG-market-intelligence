# F200 — Reimport Collection from Updated CSV

**Status:** planned
**Priority:** high
**Type:** operational (no code changes)

## Summary

Replace the current user collection (549 entries, user_id=3) with the
updated CSV at `docs/colecaoMtgAtualizada.csv` (986 rows). Some cards
were removed, many were added. The existing `import-csv` CLI command
handles the full lifecycle: snapshot old data, delete, re-insert with
auto-canonization.

## Context

- CSV format: Liga (headers match `csv_columns.py` aliases perfectly)
- Dry-run result: 986 imported, 0 skipped, 0 warnings, no price column
- Current DB: 105,870 cards (catalog), 549 collection entries
- The importer creates a `CollectionSnapshotRow` backup before replacing

## Tasks

| ID  | Description                              | Wave |
|-----|------------------------------------------|------|
| T01 | Execute collection import (replace)      | 0    |
| T02 | Post-import verification & cleanup       | 1    |

## Waves

- **Wave 0**: T01 — run the import command
- **Wave 1**: T02 — verify integrity, run orphan check

## Risks

- None significant. The importer snapshots old data before replacing.
  Cards table and price data are untouched (only `user_collection` is
  replaced). Rollback possible via snapshot.
