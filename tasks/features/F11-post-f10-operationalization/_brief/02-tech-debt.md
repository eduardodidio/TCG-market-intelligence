# 02 — Tech Debt Refactors

## Extract `_row_to_entry` (T03)

**Current state**: identical function in two files:
- `src/collectors/match_report.py:40-46`
- `src/collectors/sync_collection.py:22-28`

**Target**: create `src/collection/converter.py` with the shared function.
Both modules import from there.

Function signature:
```python
def row_to_collection_entry(row: UserCollectionRow) -> CollectionEntry:
    return CollectionEntry(
        set_code=row.set_code,
        collector_number=row.collector_number,
        name_en=row.name_en,
    )
```

## Move `collection_summary` SQLAlchemy to Repository (T04)

**Current state**: `src/api/routers/collection.py:100-142` has inline
SQLAlchemy queries (importing `select`, `Session`, `UserCollectionRow`
directly in the endpoint function body).

**Target**: add `Repository.get_collection_total_value(user_id)` that
returns `Decimal | None`. The router calls this instead of raw SQLAlchemy.

## Remove dead `BASE_URL` (T05)

**Current state**: `src/collectors/sync_collection.py:19` defines
`BASE_URL = "https://mypcards.com"` but it's never referenced.

**Target**: delete the line.
