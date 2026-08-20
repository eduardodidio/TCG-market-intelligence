# PRD: F11 - Post-F10 Operationalization

**Status:** Delivered (partial success)
**Date:** 2026-08-20
**Author:** Eduardo Rutkoski Didio
**Prerequisite:** F10 (Collection-Centric Pivot)

## Problem

F10 shipped code for collection import, match report, sync pipeline, and DB
cleanup, but the production database had not been operationalized. Set codes
were mixed-case, no match report had been run, and the collection had zero
price data. Additionally, the TechLead identified 3 minor tech debt items
during the F10 review.

## Goals

1. Normalize all set codes to lowercase in the production DB
2. Run match report to assess MYP coverage before syncing
3. Sync collection with MYP to populate price data
4. Verify dashboard shows valid collection KPIs
5. Clean up tech debt: extract duplicated converter, move raw SQLAlchemy to
   Repository, remove dead constant

## Scope

- **Operational:** run normalize, match-report, sync-collection using existing
  CLI commands against the production DB
- **Bug fix:** parser field name mismatch discovered and fixed during
  match-report execution
- **Tech debt:** 3 small refactors (no behavioral changes)
- **Documentation:** PRD, Mermaid diagrams, README update

## Constraints

- No new dependencies
- No schema changes
- All code changes are refactors -- no behavioral changes
- Operational tasks interact with MYP (rate-limited, ~45 min for sync)
- DB must be backed up before any destructive operation

## Outcomes

| Step | Result |
|------|--------|
| Set code normalization | All set codes lowercase (0 conflicts) |
| Match report (run 1) | 0% match -- parser bug discovered |
| Parser fix | `parse_search_results()` updated for MYP field names (`idproduto`, `nomeenproduto`, `slugnomeenproduto`) with backward-compatible fallback |
| Match report (run 2) | 94.7% match rate (519/548 cards) |
| Sync collection | 124 cards linked, 0 new price observations |
| Tech debt: `_row_to_entry` | Extracted to `src/collection/converter.py` |
| Tech debt: SQLAlchemy in router | Moved to `Repository.get_collection_total_value()` |
| Tech debt: dead `BASE_URL` | Removed from `sync_collection.py` |

### Parser Bug Discovery

During the first match-report run, every card returned 0 search results.
Investigation revealed `parse_search_results()` in `src/parsers/myp.py`
was reading field names (`id`, `nome`, `slug`) that no longer matched MYP's
API response (`idproduto`, `nomeenproduto`, `slugnomeenproduto`). The fix
adds a fallback chain that supports both old and new field names, with 4
new tests covering the change.

### MYP Site Change (Blocker)

During sync, 396 of 545 searched cards returned HTTP 404 on their product
pages. Furthermore, MYP's price history endpoint (`/magic/preco/{id}/{slug}`)
now redirects to the homepage -- the `window.precoChartConfig` JS variable
is no longer present. This means **0 new price observations** were collected.
The provider needs to be updated to find MYP's new data source (likely
AJAX/API endpoints). This is out of F11 scope.

## Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| AC-1 | Set codes normalized (all lowercase) | Met |
| AC-2 | Match report generated and reviewed | Met (94.7%) |
| AC-3 | Collection synced with MYP price data | Partial (124 linked, 0 observations) |
| AC-4 | Dashboard shows valid collection KPIs | Partial (card counts valid, no price data) |
| AC-5 | `_row_to_entry` extracted, no duplication | Met |
| AC-6 | `collection_summary` uses Repository | Met |
| AC-7 | Dead `BASE_URL` removed | Met |
| AC-8 | 604+ tests passing, coverage >= 90% | Met (616 tests, 91.44%) |

## Test Results

- **Backend:** 616 tests passing, 91.44% coverage
- **Frontend:** 187 tests passing
- **New tests:** 12 (4 parser, 4 converter, 4 repository)
