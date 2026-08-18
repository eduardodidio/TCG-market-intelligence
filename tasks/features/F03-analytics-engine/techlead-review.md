# Tech Lead Review -- F03 Analytics Engine

**Reviewer:** Tech Lead Agent
**Date:** 2026-08-18
**Files reviewed:** 12 files (all listed in the review scope)
**Test run:** 103/103 passed (3.28s)

---

## 1. Architecture

The analytics engine follows the planned architecture correctly:

- **Pure functions in `src/analytics/indicators.py`** -- zero database imports, zero side effects. Confirmed via grep: no `sqlalchemy`, `database`, or `Session` imports anywhere in `src/analytics/`.
- **Domain models in `src/domain/models.py`** -- new analytics dataclasses (`MovingAverage`, `PriceExtremes`, `Volatility`, `Momentum`, `CardAnalytics`) cleanly appended after existing models.
- **Repository queries in `src/database/repository.py`** -- `get_price_series()` and `get_cards_with_observations()` return domain objects, not ORM rows. Clean boundary.
- **CLI orchestration in `src/cli/main.py`** -- the `analyze` command group correctly wires repository queries to pure analytics functions. Lazy imports keep startup fast.
- **Data flow:** CLI -> Repository -> `HistoricalPrice[]` -> `indicators.py` -> `CardAnalytics` -> formatted output. Exactly as diagrammed in `F03-architecture.mmd`.

**Verdict:** Architecture is sound. No violations.

---

## 2. Code Quality

### Positive observations

- Consistent use of `Decimal` throughout -- no float contamination in financial calculations.
- All functions have docstrings explaining behavior and edge cases.
- `_extract_valid_prices()` helper centralizes None-skipping logic.
- `_print_card_analytics()` formatting is clean and handles all optional sections gracefully.
- CLI uses Click's `@click.group()` nesting (`cli` > `analyze` > `card`/`list`) correctly.

### Findings

**MINOR -- Inline imports of `timedelta` inside function bodies (indicators.py:117, 171)**

`from datetime import timedelta` is imported inside both `compute_volatility()` and `compute_momentum()` rather than at the top of the file. The `date` class is already imported at the top level. This is not a bug but violates PEP 8 convention and is inconsistent with the rest of the codebase. Moving it to the top-level imports would be cleaner.

**MINOR -- `get_observation_count` uses `text("count(*)")` (repository.py:221)**

This pre-existing method uses `select(text("count(*)"))` which is a slightly unusual SQLAlchemy pattern. Not introduced by F03, so not actionable here, but noted for awareness.

**MINOR -- `__init__.py` is empty**

The `src/analytics/__init__.py` is an empty file. Could re-export key functions for cleaner imports, but current direct imports from `indicators` are fine and explicit.

---

## 3. Testing

### Coverage summary

| Test file | Tests | Coverage area |
|-----------|-------|---------------|
| `test_analytics_models.py` | 11 | All 5 new dataclasses |
| `test_indicators.py` | 46 | All 6 indicator functions |
| `test_cli_analytics.py` | 8 | Both CLI commands (card + list) |
| `test_repository_queries.py` | 10 | Both new repository methods |
| **Total new** | **75** | |

### Edge cases covered

- Empty input lists
- All-None price series
- Single data point (insufficient data)
- Exact boundary conditions (period == data length, period == data length - 1)
- Constant prices (zero volatility)
- Trend thresholds at exactly +1% and -1% (flat boundary)
- Alternative price fields (`tcg_price`)
- Nearest-date matching for momentum when exact date not available
- Past price of zero (division by zero protection)
- CLI with no data, partial analytics, custom options, negative momentum formatting

### Observations

**MINOR -- No test for `compute_momentum` when `past_price == 0`**

The code correctly returns `None` when `past_price == 0` (line 181), but there is no explicit test for this division-by-zero guard. The behavior is correct; a test would improve documentation of intent.

**MINOR -- No test for invalid `price_field` argument**

Passing a nonexistent field name (e.g., `price_field="nonexistent"`) to any indicator function would result in `getattr` returning `None` for all prices, which correctly degrades to "no data" / `None` return. Works correctly but is not explicitly tested.

---

## 4. Security

- No hardcoded secrets, tokens, or credentials.
- No user-supplied SQL -- all queries use SQLAlchemy's parameterized statements.
- `price_field` is used with `getattr()` on dataclass instances, not in SQL. No injection risk.
- No network calls in the analytics module.
- No file I/O in the analytics module.

**Verdict:** No security concerns.

---

## 5. Correctness of Analytics Computations

### Moving Average (SMA)

Correct. `sum(last_n) / period` is the textbook simple moving average. Uses chronological order (last N values). Verified by test with known arithmetic sequence.

### Price Extremes (ATH/ATL)

Correct. Uses Python's `max()` and `min()` with key on price value. Returns both price and date. Handles ties correctly (Python's max/min return the first match, which is deterministic given stable sort).

### Volatility (Population Std Dev + CoV)

Correct. Uses population variance (`/ n`, not `/ (n-1)`), which is the right choice for "this is ALL the data we have" rather than "this is a sample." `Decimal.sqrt()` is used properly with the current decimal context. CoV = `std_dev / mean` is standard. Zero mean is guarded against.

### Momentum (Rate of Change)

Correct. `RoC = (current - past) / past * 100`. Finds nearest historical observation to the target date (N days ago), which is the right approach for sparse/weekly data. Trend thresholds at +/-1% are clearly documented and tested at boundaries.

### Potential concern (not blocking)

**MINOR -- Population vs. sample standard deviation**

The code uses population std dev (`/ n`). This is a defensible choice but should be documented explicitly in the docstring or an ADR. If the data represents a sample of a larger population (e.g., weekly snapshots of a continuous price), sample std dev (`/ (n-1)`) might be more statistically appropriate. Either way, consistency is what matters, and the code is internally consistent.

---

## 6. Diagrams

- `F03-architecture.mmd` -- Accurate flowchart showing CLI -> DB -> Analytics -> Domain Models data flow. Matches actual code structure.
- `F03-journey.mmd` -- Clean user journey from `analyze list` through card selection to `analyze card` output. Includes error paths (no cards, no data).

Both diagrams are well-structured Mermaid and reflect the implemented code.

---

## 7. README

The F03 section in `README.md` is comprehensive:
- Lists all four indicator types
- Documents new CLI commands and options
- Includes example usage with `--price-field`
- Project structure updated with `analytics/` directory
- Commands table updated with `analyze list` and `analyze card`

---

## Findings Summary

| # | Severity | Finding |
|---|----------|---------|
| 1 | MINOR | `timedelta` imported inline inside function bodies instead of at module top |
| 2 | MINOR | `__init__.py` is empty (could re-export key functions) |
| 3 | MINOR | No explicit test for `past_price == 0` in momentum |
| 4 | MINOR | No explicit test for invalid `price_field` argument |
| 5 | MINOR | Population vs. sample std dev choice not documented in docstring |

No BLOCKING or IMPORTANT findings.

---

## **Verdict: APPROVED**

The F03 Analytics Engine is well-architected, correctly implemented, thoroughly tested (75 new tests, 103 total passing), and properly documented. The analytics module maintains strict purity (no DB imports, no side effects), all computations use `Decimal` for financial precision, and edge cases are handled gracefully. The five MINOR findings are all polish items that do not affect correctness or shipping readiness.
