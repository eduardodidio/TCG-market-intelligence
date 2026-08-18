# F05 Test Plan

## 1. Test Scope

### In scope

- **New unit tests** for `src/providers/myp/provider.py` (F05-T02) — mock-based tests covering `_fetch`, `_get_session`, `close`, `discover_sets`, `discover_cards`, `get_card_details`, `get_current_price`, `get_price_history`, and `source_name`.
- **New unit tests** for `src/parsers/myp.py` (F05-T03) — edge-case and branch coverage for uncovered lines (malformed HTML, missing JSON-LD fields, empty history data, pagination edge cases).
- **New unit tests** for `src/cli/main.py` (F05-T04) — CLI runner tests for `backfill`, `update`, and `retry-failed` subcommands using mocked dependencies.
- **Regression verification** — all 131 existing tests must continue to pass after changes.
- **Housekeeping verification** (F05-T01) — `.coverage` in `.gitignore`, F03-README status corrected.
- **Documentation existence checks** (F05-T05, F05-T06) — PRDs and diagrams exist (manual/grep verification, not automated tests).

### Out of scope

- Integration or e2e tests (no new ones needed for tech debt cleanup).
- Tests for `src/analytics/indicators.py` or `src/database/repository.py` (already at acceptable coverage).
- Tests for documentation content quality (PRDs, diagrams) — verified by review, not automation.
- Any functional changes to production code.

## 2. Test Strategy

| Type | Proportion | Description |
|------|-----------|-------------|
| Unit | ~95% | Mock-based tests for provider, parser edge cases, CLI commands via CliRunner. All new tests are unit tests. |
| Integration | 0% | No new integration tests. Existing integration tests in `tests/integration/` serve as regression baseline. |
| Manual/Review | ~5% | Verify documentation artifacts exist and are valid (PRDs, `.mmd` diagrams, `.gitignore` entry, status fields). |

### Test framework and tooling

- **pytest** with `pytest-asyncio` (asyncio_mode = "auto") for async provider tests.
- **pytest-cov** for coverage measurement (`--cov=src --cov-report=term-missing`).
- **Click CliRunner** for CLI command testing.
- **unittest.mock** (`AsyncMock`, `MagicMock`, `patch`) for isolating HTTP calls and database access.
- **HTML fixtures** in `tests/fixtures/` for parser tests (reuse existing fixtures; add minimal HTML strings inline for edge cases).

## 3. Test Cases

### F05-T02: Provider tests (`tests/unit/test_provider.py`)

| ID | Description | Type | Priority | AC |
|----|-------------|------|----------|-----|
| T02-01 | `_fetch` happy path: returns `resp.text` on HTTP 200 | Unit | HIGH | AC2 |
| T02-02 | `_fetch` retries on HTTP 429, succeeds on retry | Unit | HIGH | AC2 |
| T02-03 | `_fetch` retries on HTTP 403, succeeds on retry | Unit | HIGH | AC2 |
| T02-04 | `_fetch` raises `RuntimeError` after exhausting retries on 4xx/5xx | Unit | HIGH | AC2 |
| T02-05 | `_fetch` raises `RuntimeError` after Timeout/OSError retries exhausted | Unit | HIGH | AC2 |
| T02-06 | `_fetch` respects rate-limit delay between requests | Unit | MEDIUM | AC2 |
| T02-07 | `_get_session` creates session lazily and reuses it | Unit | MEDIUM | AC2 |
| T02-08 | `close` closes session and sets it to None | Unit | MEDIUM | AC2 |
| T02-09 | `close` is no-op when session is already None | Unit | LOW | AC2 |
| T02-10 | `discover_sets` returns set slugs from paginated HTML | Unit | HIGH | AC2 |
| T02-11 | `discover_sets` handles single-page response (no pagination) | Unit | MEDIUM | AC2 |
| T02-12 | `discover_cards` returns `SourceCard` list from set page | Unit | HIGH | AC2 |
| T02-13 | `_discover_cards_in_set` handles multi-page with dedup | Unit | MEDIUM | AC2 |
| T02-14 | `get_card_details` calls `_fetch` and delegates to `parse_card_page` | Unit | HIGH | AC2 |
| T02-15 | `get_current_price` calls `_fetch` and delegates to `parse_price_snapshot` | Unit | HIGH | AC2 |
| T02-16 | `get_price_history` calls `_fetch` and delegates to `parse_price_history` | Unit | HIGH | AC2 |
| T02-17 | `source_name` returns `"myp"` | Unit | LOW | AC2 |

### F05-T03: Parser edge-case tests (`tests/unit/test_parsers.py`)

| ID | Description | Type | Priority | AC |
|----|-------------|------|----------|-----|
| T03-01 | `parse_json_ld_product` with missing/empty JSON-LD script tag | Unit | HIGH | AC3 |
| T03-02 | `parse_json_ld_product` with malformed JSON in script tag | Unit | HIGH | AC3 |
| T03-03 | `parse_json_ld_product` with missing required fields (name, sku, etc.) | Unit | MEDIUM | AC3 |
| T03-04 | `parse_price_snapshot` with no price data in HTML | Unit | HIGH | AC3 |
| T03-05 | `parse_price_history` with missing `precoChartConfig` JS variable | Unit | HIGH | AC3 |
| T03-06 | `parse_price_history` with empty labels/series arrays | Unit | MEDIUM | AC3 |
| T03-07 | `parse_card_links` with empty page (no card links) | Unit | MEDIUM | AC3 |
| T03-08 | `parse_set_links` with empty page (no set links) | Unit | MEDIUM | AC3 |
| T03-09 | `parse_pagination_max` with no pagination links | Unit | MEDIUM | AC3 |
| T03-10 | `parse_card_page` with partial/incomplete HTML structure | Unit | MEDIUM | AC3 |
| T03-11 | `parse_sku` with unexpected SKU format variations | Unit | LOW | AC3 |

### F05-T04: CLI tests (`tests/unit/test_cli.py` or extended `test_cli_analytics.py`)

| ID | Description | Type | Priority | AC |
|----|-------------|------|----------|-----|
| T04-01 | `backfill` command invokes `run_backfill` with correct args | Unit | HIGH | AC4 |
| T04-02 | `backfill --set <slug>` passes set filter correctly | Unit | HIGH | AC4 |
| T04-03 | `backfill --concurrency N` passes concurrency parameter | Unit | MEDIUM | AC4 |
| T04-04 | `backfill --no-resume` disables resume behavior | Unit | MEDIUM | AC4 |
| T04-05 | `update` command invokes update flow with mocked deps | Unit | HIGH | AC4 |
| T04-06 | `retry-failed` command invokes retry flow with mocked deps | Unit | HIGH | AC4 |
| T04-07 | CLI commands handle errors gracefully (non-zero exit code, message) | Unit | MEDIUM | AC4 |
| T04-08 | CLI `backfill` prints summary output on success | Unit | LOW | AC4 |

### F05-T01: Housekeeping (verified manually or via grep)

| ID | Description | Type | Priority | AC |
|----|-------------|------|----------|-----|
| T01-01 | `.coverage` entry exists in `.gitignore` | Manual | LOW | AC8 |
| T01-02 | F03-README.md status is "done" | Manual | LOW | AC9 |
| T01-03 | No other stale status fields in F01/F02/F04 READMEs | Manual | LOW | AC9 |

### Cross-cutting

| ID | Description | Type | Priority | AC |
|----|-------------|------|----------|-----|
| X-01 | All 131 existing tests still pass after new tests are added | Regression | CRITICAL | AC5 |
| X-02 | Overall project coverage >= 90% | Coverage | CRITICAL | AC1 |
| X-03 | `ruff check` reports 0 lint errors on new test files | Lint | HIGH | AC5 |

## 4. Coverage Targets

| Module | Current | Target | AC |
|--------|---------|--------|-----|
| `src/providers/myp/provider.py` | 63% | >= 85% | AC2 |
| `src/parsers/myp.py` | 82% | >= 90% | AC3 |
| `src/cli/main.py` | 77% | >= 85% | AC4 |
| `src/collectors/backfill.py` | 89% | >= 90% | AC1 (stretch) |
| **Overall (`src/`)** | **86%** | **>= 90%** | **AC1** |

Coverage will be measured with: `pytest --cov=src --cov-report=term-missing`

Per-module verification: `pytest --cov=src/providers/myp/provider --cov-report=term-missing tests/unit/test_provider.py`

## 5. Test Data & Fixtures

### Existing fixtures (reuse)

Located in `tests/fixtures/`:
- `card_page_one_ring.html` — full card detail page with JSON-LD
- `price_history_one_ring.html` — history page with `precoChartConfig`
- `set_page_dmr.html` — set page with card links
- `editions_page_1.html` — editions listing with set links and pagination

### New fixtures needed

| Fixture | Purpose | Format |
|---------|---------|--------|
| Minimal valid HTML for `_fetch` tests | Provider mock responses | Inline strings in test file |
| Malformed JSON-LD HTML | Parser edge case (T03-02) | Inline string |
| HTML without JSON-LD script tag | Parser edge case (T03-01) | Inline string |
| HTML without `precoChartConfig` | History edge case (T03-05) | Inline string |
| Empty set/card page HTML | Parser edge case (T03-07, T03-08) | Inline string |
| Multi-page set HTML (page 1 and 2) | Provider pagination (T02-10) | Inline strings |

Most edge-case fixtures should be **inline minimal HTML strings** in the test file, not full-page fixtures. This keeps them readable and self-documenting.

### Mock patterns

- **Provider tests**: Patch `curl_cffi.requests.AsyncSession` to return `MagicMock` responses with controlled `status_code` and `text`.
- **CLI tests**: Patch `src.cli.main.run_backfill` (and equivalent update/retry functions) with `AsyncMock`. Use Click's `CliRunner` for invocation.
- **Parser tests**: No mocks needed — pure functions receiving HTML strings.

## 6. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Mock fidelity: mocked `AsyncSession` may not match `curl_cffi` behavior | Tests pass but real behavior differs | Medium | Keep mocks minimal; test only the contract (status_code, text). Use real fixture HTML for parse verification. |
| Async test complexity: `pytest-asyncio` edge cases with event loops | Flaky tests or test hangs | Low | Use `asyncio_mode = "auto"` (already configured). Set `delay_seconds=0` to avoid real sleeps. Set `max_retries=2` to keep retry tests fast. |
| Coverage measurement: per-file vs overall may not reconcile | Individual targets met but overall misses 90% | Low | Run final full-suite coverage check. The 4 target modules account for most of the gap from 86% to 90%. |
| New test file placement: wrong location breaks test discovery | Tests not discovered by pytest | Low | Follow existing convention: `tests/unit/test_<module>.py`. Verify with `pytest --collect-only`. |
| Fixture HTML drift: fixtures become stale if source site changes format | Tests pass on stale fixtures, fail on real HTML | Low | Acceptable for unit tests. Integration tests (existing) cover real-format concerns. |
| Pre-commit hooks reject new files on formatting | Commit fails, developer confusion | Very Low | Run `ruff format` on new test files before committing. |

## 7. Exit Criteria

All of the following must be true for F05 testing to be considered complete:

1. **All new test cases pass**: `pytest` exits with 0 (all tests green, including the original 131).
2. **Coverage targets met**:
   - `provider.py` >= 85%
   - `parsers/myp.py` >= 90%
   - `cli/main.py` >= 85%
   - Overall `src/` >= 90%
3. **Zero lint errors**: `ruff check tests/` reports no issues on new test files.
4. **Housekeeping verified**: `.coverage` in `.gitignore`, F03-README status is "done".
5. **Documentation artifacts exist**: PRDs for F02, F03, F04 in `docs/prd/`; diagrams `F04-architecture.mmd` and `F04-journey.mmd` in `docs/diagrams/`.
6. **No test pollution**: new tests do not modify global state, create temp files outside `tmp_path`, or depend on test execution order.
