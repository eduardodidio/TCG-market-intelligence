# F03 Test Plan -- Analytics Engine

**Status:** retroactive
**Generator:** TEA (Test Architect)
**Generated at:** 2026-08-18
**Source brief:** F03 adds pure-function analytics indicators (moving averages, ATH/ATL, volatility, momentum) over collected price time-series, with CLI integration and no database coupling inside the analytics module.

---

## 1. Fixtures

| Fixture | Path | Domain | Owner |
|---------|------|--------|-------|
| `thirty_daily_prices` | `tests/unit/test_indicators.py` | 30 daily prices incrementing by R$0.50 from R$10.00 | F03-T03 |
| `constant_prices` | `tests/unit/test_indicators.py` | 10 daily prices all R$5.00 (zero volatility, flat trend) | F03-T03 |
| `prices_with_nones` | `tests/unit/test_indicators.py` | 10 prices with 3 None gaps (tests None-skipping) | F03-T03 |
| `empty_prices` | `tests/unit/test_indicators.py` | Empty list (boundary: no data at all) | F03-T03 |
| `all_none_prices` | `tests/unit/test_indicators.py` | 10 entries, all `median_price=None` | F03-T03 |
| `single_price` | `tests/unit/test_indicators.py` | Single observation (insufficient for volatility/momentum) | F03-T03 |
| `_hp()` helper | `tests/unit/test_indicators.py` | Factory for `HistoricalPrice` with configurable fields | F03-T03 |
| `_make_prices()` helper | `tests/unit/test_indicators.py` | Factory for daily price lists from value arrays | F03-T03 |
| `repo` (tmp_path SQLite) | `tests/unit/test_repository_queries.py` | In-memory Repository for integration queries | F03-T02 |
| `_make_price()` helper | `tests/unit/test_repository_queries.py` | Factory for `HistoricalPrice` with date/median | F03-T02 |
| `_make_analytics()` helper | `tests/unit/test_cli_analytics.py` | Full `CardAnalytics` object for CLI output formatting tests | F03-T04 |

**Justification:** Each fixture prevents rework by centralizing test data construction. The `_hp()` factory is the most critical -- it enables 46 indicator tests to construct `HistoricalPrice` objects with a single call, avoiding 200+ lines of boilerplate.

---

## 2. Harnesses por fronteira

### Unit

- **Framework:** pytest
- **Command:** `python -m pytest tests/unit/ -v`
- **Default test path:** `tests/unit/`
- **Test files:**
  - `test_analytics_models.py` (11 tests) -- dataclass instantiation and field validation
  - `test_indicators.py` (46 tests) -- all 6 pure indicator functions
  - `test_cli_analytics.py` (8 tests) -- CLI output formatting with mocked Repository

### Integration

- **Framework:** pytest
- **Command:** `python -m pytest tests/unit/test_repository_queries.py -v`
- **Default test path:** `tests/unit/test_repository_queries.py`
- **Test files:**
  - `test_repository_queries.py` (10 tests) -- `get_price_series` and `get_cards_with_observations` against a real SQLite database (in-memory via `tmp_path`)
- **Note:** These are integration tests despite living in `tests/unit/`. They exercise SQLAlchemy ORM against a real SQLite engine. Consider moving to `tests/integration/` in a future refactor for clearer boundary separation.

### E2E

**N/A** -- The analytics engine is a CLI tool operating on a local SQLite database. There are no external services, no network calls, and no multi-process orchestration. The CLI smoke tests documented in the QA report (section 2) serve as manual E2E validation against the production database. Automated E2E would not prevent rework beyond what the unit + integration tests already cover.

---

## 3. Perf budgets

| Metrica | Limite | Como medir | Aplicavel a |
|---------|--------|------------|-------------|
| Full test suite | < 5s | `python -m pytest tests/ --durations=10` | All 103 tests |
| Single indicator function | < 10ms per 1000 observations | Manual benchmark with `timeit` | `compute_volatility`, `compute_momentum` (Decimal sqrt is the costliest op) |

**Note:** Current suite runs in ~3.2s. No individual test is performance-sensitive at current data volumes (max 1889 observations per card). Perf budgets become relevant if card histories grow to 10k+ observations, at which point the `_extract_valid_prices` linear scan and `min()` in `compute_momentum` would dominate.

---

## 4. Mocks vs hits real

| Componente | Decisao | Justificativa |
|------------|---------|---------------|
| `src/analytics/indicators.py` | real | Pure functions with no side effects. Mocking would test nothing. |
| `src/domain/models.py` | real | Dataclasses with no behavior to mock. |
| `src/database/repository.py` (in indicator tests) | N/A | Analytics module has zero DB imports -- no decision needed. |
| `src/database/repository.py` (in repository query tests) | real | Tests use real SQLite via `tmp_path`. Real is correct here: the queries contain SQLAlchemy logic (ORDER BY, GROUP BY, date filtering) that a mock would not exercise. |
| `src/database/repository.Repository` (in CLI tests) | mock | CLI tests mock `Repository` to avoid filesystem/DB setup. Justified: CLI tests verify output formatting and option wiring, not query correctness (covered by repository query tests). |
| `src/analytics.indicators.compute_card_analytics` (in CLI tests) | mock | CLI happy-path test mocks the orchestrator to control output and verify formatting in isolation. |

---

## 5. Test scenarios resumo

### F03-T01 (Domain Models) -- 11 tests

1. Instantiate `MovingAverage` with valid data, verify all fields (F03-T01)
2. `MovingAverage` with zero value (F03-T01)
3. Instantiate `PriceExtremes` with valid data (F03-T01)
4. `PriceExtremes` with zero prices (F03-T01)
5. Instantiate `Volatility` with valid data (F03-T01)
6. Instantiate `Momentum` with up/down/flat trends (F03-T01)
7. `Momentum` with negative `rate_of_change` (F03-T01)
8. `CardAnalytics` with defaults (empty MA list, None optionals) (F03-T01)
9. `CardAnalytics` with empty `moving_averages` list (F03-T01)
10. `CardAnalytics` fully populated (F03-T01)
11. `CardAnalytics.computed_at` auto-set to now (F03-T01)

### F03-T02 (Repository Queries) -- 10 tests

12. `get_price_series` returns ordered by date ASC (F03-T02)
13. `get_price_series` returns `HistoricalPrice` domain objects (F03-T02)
14. `get_price_series` filters by `days` parameter (F03-T02)
15. `get_price_series` with `days=0` returns only today (F03-T02)
16. `get_price_series` for nonexistent card returns `[]` (F03-T02)
17. `get_price_series` single observation (F03-T02)
18. `get_price_series` filters by source and external_id (F03-T02)
19. `get_cards_with_observations` returns (id, count) tuples (F03-T02)
20. `get_cards_with_observations` empty source returns `[]` (F03-T02)
21. `get_cards_with_observations` filters by source (F03-T02)

### F03-T03 (Analytics Indicators) -- 46 tests

22-32. `compute_moving_average`: happy path (constant, 30-point, exact boundary), insufficient data, empty, all-None, period-1, skips None, alternative field, calculated_at date (F03-T03)
33-36. `compute_all_moving_averages`: default periods, custom periods, empty, all-None (F03-T03)
37-42. `compute_price_extremes`: finds ATH/ATL, constant (ATH==ATL), empty, all-None, skips None, alternative field (F03-T03)
43-50. `compute_volatility`: known std_dev, constant zero, fewer-than-2, empty, all-None, period_days filter, skips None, Decimal type check (F03-T03)
51-63. `compute_momentum`: positive RoC, negative RoC, constant flat, exactly +1% flat, exactly -1% flat, just above +1% up, just below -1% down, single price, empty, all-None, skips None, nearest-date matching, alternative field (F03-T03)
64-68. `compute_card_analytics`: full assembly, empty, all-None, alternative field, computed_at set (F03-T03)

### F03-T04 (CLI Analytics) -- 8 tests

69. `analyze card` happy path -- all sections printed with correct formatting (F03-T04)
70. `analyze card` with no data -- friendly message (F03-T04)
71. `analyze card` with custom options `--db`, `--source`, `--price-field` (F03-T04)
72. `analyze card` negative momentum formatting (no `+` sign) (F03-T04)
73. `analyze card` partial analytics (None sections omitted) (F03-T04)
74. `analyze list` happy path -- cards table with counts (F03-T04)
75. `analyze list` no cards -- friendly message (F03-T04)
76. `analyze list` custom `--source` (F03-T04)

### F03-T05 (Diagrams + README) -- 0 automated tests

No automated tests. Validated by manual review (QA report section 3, AC5/AC6).

### Identified gaps (not currently tested)

- **GAP-1: `past_price == 0` in `compute_momentum`** (line 181 of `indicators.py`). The code returns `None` to guard against division by zero. No test exercises this branch. **Severity: low.** The guard is a 2-line conditional with obvious correctness. **Recommended test:** Build two `HistoricalPrice` objects where the past observation has `median_price=Decimal("0")` and verify `compute_momentum` returns `None`.

- **GAP-2: Invalid `price_field` argument.** Passing `price_field="nonexistent_field"` to any indicator function causes `getattr(hp, "nonexistent_field", None)` to return `None` for all entries, which degrades gracefully to the "no valid data" path (returns `None`). Correct behavior, but no test documents this contract explicitly. **Severity: low.** The `getattr` with `None` default is Python-standard and unlikely to regress. **Recommended test:** Call `compute_moving_average(prices, period=5, price_field="does_not_exist")` and assert `None` return.

- **GAP-3: `_extract_valid_prices` helper not directly tested.** This function is the foundation of all indicators but has no dedicated test class. It is thoroughly exercised indirectly through 46 indicator tests (empty, all-None, mixed-None, alternative field). **Severity: negligible.** Direct tests would add ceremony without preventing rework. No action recommended.

- **GAP-4: `compute_volatility` with all-zero valid prices.** The `mean == 0` guard (line 137-138) sets `coefficient_of_variation = Decimal("0")`. The `constant_prices` fixture uses `Decimal("5.00")`, so this exact branch is only tested when `std_dev` happens to be zero (which it is, making `coeff_var = 0/5 = 0`). A test with all-zero prices would exercise the `mean == 0` guard directly. **Severity: low.** The guard is trivial.

- **GAP-5: `pytest-cov` not installed.** Automated branch coverage measurement is unavailable. The QA report notes this. Adding `pytest-cov` to dev dependencies would make coverage tracking automatic for future features. **Severity: tooling improvement, not a test gap.**

---

## 6. Anotacoes para tasks

| Task | Fixtures needed |
|------|----------------|
| F03-T01 | _(none -- dataclass tests use inline construction)_ |
| F03-T02 | `repo` (tmp_path SQLite), `_make_price` helper |
| F03-T03 | `thirty_daily_prices`, `constant_prices`, `prices_with_nones`, `empty_prices`, `all_none_prices`, `single_price`, `_hp` helper |
| F03-T04 | `_make_prices` helper, `_make_analytics` helper, mock `Repository`, mock `compute_card_analytics` |
| F03-T05 | _(no automated tests -- documentation task)_ |

---

## Risks for QA

1. **Population vs. sample std dev** -- TechLead noted the code uses population std dev (`/n`) rather than sample (`/(n-1)`). This is a defensible design choice for "all data we have" but is not documented in the function docstring or an ADR. If a future contributor changes this, existing tests will break because they assert exact Decimal values. The choice should be documented.

2. **`datetime.now()` in `compute_card_analytics`** -- The orchestrator calls `datetime.now()` to set `computed_at`. This makes the `test_computed_at_set` test nondeterministic (it asserts `is not None` rather than an exact value). Not a bug, but if future tests need to assert exact timestamps, the function should accept an optional `now` parameter or the test should freeze time.

3. **Inline `timedelta` imports** -- `from datetime import timedelta` is imported inside `compute_volatility` and `compute_momentum` function bodies. This is a cosmetic issue (PEP 8 violation) that does not affect test correctness but may confuse contributors.
