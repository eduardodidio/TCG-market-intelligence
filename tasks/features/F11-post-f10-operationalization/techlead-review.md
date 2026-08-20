# TechLead Review: F11 -- Post-F10 Operationalization

**Reviewer:** TechLead Agent
**Date:** 2026-08-20
**Verdict:** APPROVED

---

## Summary

F11 is a clean operationalization feature: it ran existing pipelines against
production data, discovered and fixed a real parser bug, resolved all 3 tech
debt items from the F10 TechLead review, and documented a significant upstream
blocker (MYP site changes). The code changes are minimal, well-tested, and
architecturally consistent.

---

## Checklist

| Item | Status |
|------|--------|
| Tests pass (616 backend, 187 frontend) | PASS |
| Coverage >= 90% (91.44%) | PASS |
| Ruff lint (0 errors) | PASS |
| No raw SQLAlchemy in API layer | PASS |
| No duplicated `_row_to_entry` | PASS |
| Dead `BASE_URL` removed | PASS |
| PRD delivered | PASS |
| Architecture diagram delivered | PASS |
| Journey diagram delivered | PASS |
| README updated with F11 notes | PASS |

---

## Findings

### Parser Fix (GOOD)

The `parse_search_results()` fix in `src/parsers/myp.py` is well-designed.
The fallback chain (`idproduto` -> `id`, `nomeenproduto` -> `nomeptproduto`
-> `nome`, etc.) maintains backward compatibility with the old field names
used in test fixtures while correctly handling the new MYP API shape. This
means existing tests against `myp_search_bolt.json` and
`myp_search_single.json` (which use old field names) continue to pass,
while the 4 new tests in `TestParseSearchResultsNewFieldNames` exercise the
new field names.

One observation: the `codigoproduto` field (new MYP name for `sku`) uses
the same fallback pattern. Line 75 correctly handles both:
`item.get("codigoproduto") or item.get("sku") or None`.

### Converter Extraction (GOOD)

`src/collection/converter.py` is a clean single-function module. The
function `row_to_collection_entry()` is the single source of truth for the
`UserCollectionRow -> CollectionEntry` mapping. Both `match_report.py` and
`sync_collection.py` import from the same location. The 3 test cases in
`test_converter.py` cover the happy path, `None` name, and empty set code.

The tests in `test_match_report.py` and `test_sync_collection.py` also
import and use `row_to_collection_entry` from the converter, confirming no
stale references remain.

### Repository.get_collection_total_value() (GOOD)

The method correctly:
- Returns `None` when no linked cards exist
- Returns `None` when linked cards have no prices
- Sums `median_price * quantity` for linked cards with prices
- Delegates to existing `get_latest_prices_batch()` for price lookup

The 5 test cases in `TestGetCollectionTotalValue` cover: happy path, no
linked cards, linked cards without prices, mixed (some priced / some not),
and unlinked entries. This is thorough.

The router in `collection.py` line 103 now calls
`repo.get_collection_total_value(FAKE_USER_ID)` instead of inline
SQLAlchemy, which resolves the F10 layering violation flagged as IMPORTANT.

### Documentation (GOOD)

- PRD is well-structured and honestly documents partial success (0 new
  observations due to MYP site changes)
- Architecture diagram accurately shows the blocked state at the price
  history step
- Journey diagram includes the parser-fix feedback loop
- README F11 section clearly states the MYP blocker

---

## MINOR Notes

1. **Fixture files still use old field names.** The test fixture files
   `myp_search_bolt.json` and `myp_search_single.json` use the old MYP
   field names (`id`, `nome`, `slug`, `sku`). This is correct for backward
   compatibility testing, but consider adding a fixture file with new field
   names (e.g., `myp_search_new_format.json`) in a future feature so that
   the fixture-based tests also exercise the primary code path. Currently
   the new field names are only tested via inline `json.dumps()` in
   `TestParseSearchResultsNewFieldNames`. This is not a blocker.

2. **ResourceWarning in test output.** The test run produces 86 warnings,
   most of which are `ResourceWarning: unclosed database` from SQLAlchemy
   sessions in test fixtures. This is a pre-existing condition (not caused
   by F11) and should be addressed in a future tech debt pass -- likely by
   adding `engine.dispose()` in test teardown or using `StaticPool`.

---

## Follow-Up Items (Future Features)

1. **MYP price history is broken.** The sync pipeline successfully matches
   and links cards, but collects 0 price observations because MYP's
   `/magic/preco/{id}/{slug}` endpoint now redirects to the homepage.
   Additionally, 396 of 545 card product pages return HTTP 404. A future
   feature must investigate MYP's new data endpoints (likely AJAX/API)
   and update the provider accordingly. This is the highest-priority
   follow-up.

2. **N+1 query in `get_latest_prices_batch()`** -- This method iterates
   `card_ids` one by one, issuing 2 queries per card. For the
   `get_collection_total_value()` use case this is fine (collection sizes
   are small), but if collection sizes grow significantly, consider a
   single batch query. Pre-existing from F10.

3. **New fixture file for new MYP API format** -- See MINOR note 1 above.

---

## Verdict: APPROVED

F11 is approved. All 3 tech debt items are properly resolved, the parser fix
is backward-compatible, test coverage is strong at 91.44%, and the MYP site
change blocker is documented honestly. The code changes are minimal and
architecturally consistent with the established patterns.
