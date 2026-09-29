# F185 Tech Lead Review -- Movers Percentage Integrity Fix

**Reviewer:** Tech Lead
**Date:** 2026-09-29
**Verdict:** APPROVED

## Summary

The implementation correctly aligns `get_movers()` with `get_collection_movers_optimized()` by adding both the R$0.50 price floor (SQL-level `WHERE`) and the +/-1000% percentage cap (post-query Python filter). Price insertion validation and the diagnostic CLI are clean, well-scoped additions. Test coverage is thorough with good boundary-value testing.

## Checklist

| # | Check | Result |
|---|-------|--------|
| 1 | `get_movers()` matches `get_collection_movers_optimized()` filters | PASS -- both use `price_start >= 0.5` in SQL WHERE clause and `abs(change_pct) <= 1000.0` post-query filter |
| 2 | Price validation rejects `median_price <= 0`, allows `None` | PASS -- line 405: `if p.median_price is not None and p.median_price <= 0` correctly skips bad values while allowing None through |
| 3 | No side effects on existing functionality | PASS -- price floor change is stricter than the old `> 0` filter, cap is additive; both are safe narrowing of results |
| 4 | Tuple index correct (index 6 for `change_pct`) | PASS -- tuple is `(card_id, name_en, name_pt, set_code, price_start, price_end, change_pct)` so index 6 is correct (line 1083) |
| 5 | CLI `diagnose-prices` is read-only | PASS -- uses only SELECT queries via `session.query()`, no inserts/updates/deletes; verified by test `TestDiagnosePricesReadOnly` |
| 6 | CLI follows Click conventions | PASS -- uses `@cli.command`, `@click.option` with `--db` callback, `--limit` with default, `click.echo` for output |
| 7 | Structlog logger properly used | PASS -- `logger = structlog.get_logger()` at module level (line 8), `logger.warning("skipping_invalid_price", ...)` at line 406 |
| 8 | Tests cover edge cases and boundaries | PASS -- see details below |
| 9 | Diagrams valid and accurate | PASS -- both .mmd files are syntactically correct Mermaid flowcharts |

## Issues Found

No critical or blocking issues.

### Minor observations (informational, non-blocking)

1. **Severity:** minor
   **File:** `src/database/repository.py` line 1076
   **Description:** The price floor `earliest.c.price_start >= 0.5` uses a Python float literal in an SQLAlchemy comparison. This works correctly for both SQLite and PostgreSQL, but using `Decimal("0.5")` would be more consistent with the codebase's use of Decimal for monetary values. Not a functional issue since the comparison is coerced properly by both dialects.
   **Fix suggestion:** Optional -- `earliest.c.price_start >= Decimal("0.5")` for stylistic consistency.

2. **Severity:** minor
   **File:** `src/database/repository.py` lines 1082-1083
   **Description:** The percentage cap is applied in Python (`abs(m[6]) <= 1000.0`) after fetching all rows from the database. For `get_collection_movers_optimized()` this is fine since it is user-scoped, and for `get_movers()` the result set is bounded by the `price_start >= 0.5` filter. However, if the data grows significantly, a SQL-level `HAVING` clause on the `change_pct` expression could reduce data transfer. This is an optimization opportunity, not a bug.

3. **Severity:** minor
   **File:** `src/cli/main.py` line 3421
   **Description:** Division-by-zero guard `if row.min_price else 0` is defensive but the query already filters `median_price > 0`, so `min_price` should never be zero. The guard is good practice regardless.

## Test Coverage Assessment

- **`test_market_movers_filters.py`** (236 lines, 9 tests): Excellent coverage of price floor (exact boundary at 0.49/0.50), percentage cap (exact boundary at 1000/1001%), happy-path sorting, and combined filter behavior. The note about negative percentages being bounded by zero is correct and well-documented.

- **`test_market_endpoints_filters.py`** (528 lines, 12 tests): Good integration-level tests covering all three market endpoints (`/movers`, `/summary`, `/volatile`) plus the service layer delegation. Tests verify that the repo-level fix propagates through the stack. The mock approach is appropriate since T01 handles the actual filtering.

- **`test_price_validation.py`** (132 lines, 8 tests): Comprehensive validation tests including zero, negative, None, valid values, mixed batches, structlog warning verification, and edge case that `tcg_price`/`last_sold_price` are NOT filtered (only `median_price`).

- **`test_cli_diagnose.py`** (239 lines, 6 tests): Covers penny price detection, extreme ratio detection, clean data, `--limit` option, and the critical read-only assertion. The monkeypatch approach for injecting the engine is slightly unconventional but functional.

## Positive Notes

- The fix is minimal and surgical. Rather than rewriting `get_movers()`, it adds the two missing guards that `get_collection_movers_optimized()` already had, achieving parity with the least amount of change.

- Defense-in-depth approach for price validation is sound: providers filter at parse time, but the repository now provides a second validation layer. The decision to reject only `median_price <= 0` (not other fields) and to allow `None` is correct for the domain.

- The `diagnose-prices` CLI is a useful operational tool that follows existing CLI patterns (`--db` with `_resolve_db` callback, lazy imports). Being read-only is the right call for a diagnostic command.

- Test boundary values are precise: 0.49 vs 0.50, 1000% vs 1001%. This is exactly the kind of testing that catches off-by-one errors.

- Both Mermaid diagrams accurately reflect the architecture (filter points in the data flow) and the operator journey (diagnostic workflow). They are concise and informative.
