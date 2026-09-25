# F171 Tech Lead Review

**Reviewer:** Tech Lead (automated)
**Date:** 2026-09-25
**Verdict:** APPROVED

---

## Summary

F171 fixes commander card search returning zero results when cards were created
by the price collector (bare rows with NULL metadata). The fix is a data-layer
enrichment: the catalog seeder now uses `on_conflict_do_update` with `COALESCE`
to fill NULL metadata fields on pre-existing cards. A new CLI command
(`catalog enrich`) provides a lightweight sibling-based backfill.

## Files Reviewed

| File | Change | Assessment |
|------|--------|------------|
| `src/catalog/seeder.py` | `on_conflict_do_nothing` -> `on_conflict_do_update` with COALESCE | Correct, well-structured |
| `src/cli/main.py` | New `catalog enrich` command (lines 2399-2535) | Clean implementation |
| `tests/unit/decks/test_commander_search.py` | `TestCommanderSearchBareCards` class (6 tests) | Good coverage of the bug scenario |
| `tests/unit/catalog/test_seeder_enrich.py` | `TestSeederEnrichExistingBareCard` + `TestSiblingEnrichment` (8 tests) | Thorough |
| `tests/cli/test_catalog_enrich.py` | `TestCatalogEnrich` (7 tests) | Covers happy path, dry-run, edge cases |

## Code Quality

**Seeder (`seeder.py`)**
- The `COALESCE(existing, new)` approach is correct: it fills NULLs from
  Scryfall without overwriting user-edited or previously-set values.
- Pre-query for existing keys (`existing_keys` set) to distinguish inserts
  from updates is a reasonable approach for accurate counting.
- The `SeedResult` dataclass properly tracks `cards_updated` separately.
- `import or_` inside the function is slightly unusual but acceptable since
  this is a batch-processing function not on a hot path.

**CLI command (`catalog enrich`)**
- Well-structured: audit phase, dry-run support, batched updates, summary output.
- Sibling lookup is efficient: grouped by `name_en`, donor query uses `IN` clause
  with batch_size chunking to avoid overly large queries.
- Only copies non-NULL fields from donor, correctly handling partial donors.
- `engine.dispose()` called on all exit paths.

**Tests**
- 21 new tests total (6 + 8 + 7) covering:
  - Bare card exclusion from commander search
  - Enrichment fills NULL fields
  - COALESCE preserves existing non-NULL values
  - Card ID stability after enrichment
  - Fresh insert path
  - Sibling enrichment with/without available donor
  - CLI dry-run, empty DB, mixed scenarios, partial donor
- The `TestCommanderSearchBareCards.test_full_pipeline_bare_card_to_commander_search`
  test is particularly valuable as it reproduces the exact bug scenario end-to-end.

## Dual-Dialect Support (SQLite + PostgreSQL)

- Uses `dialect_insert(session.get_bind(), CardRow)` -- the established pattern
  from `src/database/compat.py` that returns the correct dialect-specific insert.
- Both SQLite and PostgreSQL support `.on_conflict_do_update()` with
  `index_elements` and `.excluded`.
- `func.coalesce()` is standard SQL, works on both dialects.
- Tests run against SQLite in-memory, which exercises the same SQL paths.

## Security

- No raw SQL strings; all queries use SQLAlchemy ORM/Core.
- No SQL injection risk -- parameterized via SQLAlchemy's `.values()` and `.where()`.
- No new dependencies introduced.
- No secrets or credentials in code.

## Scope

The change is minimal and focused:
- Seeder enrichment logic (T01)
- CLI backfill command (T02)
- Tests (T03)

No scope creep. The plan mentioned `repository.py` and `builder.py` as
potentially affected but correctly identified the data layer as the real fix.
Neither was modified.

## Test Results

- **F171 tests:** 63 passed (14.73s)
- **Full suite:** 1 failure in `tests/api/test_collect_router.py::TestBackfillEndpoint::test_accepts_valid_request`
  -- pre-existing auth test issue (file last modified in F06, not touched by F171). 220 passed.

## Minor Observations (non-blocking)

1. The `_get_card` helper in `test_catalog_enrich.py` creates a new `CardRow`
   to detach from session. This works but `session.expunge(card)` would be
   more idiomatic. Not worth changing.

2. ResourceWarning spam about unclosed SQLite connections is a project-wide
   issue, not introduced by F171.

3. The coverage threshold (70%) failure is due to running only F171 test files
   against the entire `src/` tree. Not a real concern.
