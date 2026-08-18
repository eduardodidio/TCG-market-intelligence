# TechLead Review -- F05

**Verdict:** APPROVED
**Reviewed at:** 2026-08-18T14:30:00

## Acceptance Criteria Checklist

- [x] AC1: Overall test coverage >= 90% -- **PASS** (97.21%, well above target)
- [x] AC2: `provider.py` coverage >= 85% -- **PASS** (100%)
- [x] AC3: `parsers/myp.py` coverage >= 90% -- **PASS** (100%)
- [x] AC4: `cli/main.py` coverage >= 85% -- **PASS** (99%, only line 192 `cli()` main-guard uncovered)
- [x] AC5: All existing 131 tests still pass -- **PASS** (213 total, all passing)
- [x] AC6: PRDs exist for F02, F03, F04 in `docs/prd/` -- **PASS**
- [x] AC7: `F04-architecture.mmd` and `F04-journey.mmd` exist in `docs/diagrams/` -- **PASS**
- [x] AC8: `.coverage` is in `.gitignore` -- **PASS** (line 10)
- [x] AC9: F03-README.md status updated to "done" -- **PASS** (line 3: `**Status:** done`)

## File Reviews

### `.gitignore`
- Quality: HIGH
- `.coverage` added at line 10. No issues.

### `tasks/features/F03-analytics-engine/F03-README.md`
- Quality: HIGH
- Status correctly reads "done". No other changes.

### `tests/unit/test_provider.py`
- Quality: HIGH
- Coverage: achieves 100% on `provider.py` (target was 85%).
- Mock fidelity: mocks are applied at the correct layer (`_session` injection for `_fetch` tests, `parse_*` patches at the import point for `get_card_details`/`get_current_price`/`get_price_history`). This is the right approach -- it isolates the provider logic from parser logic and network I/O.
- Test structure: well-organized into classes by method (`TestFetch`, `TestDiscoverSets`, `TestDiscoverCards`, `TestGetCardDetails`, `TestGetCurrentPrice`, `TestGetPriceHistory`, `TestMypConfig`). Each class covers happy path, error path, and boundary conditions.
- Assertions: strong -- checks return values, call counts, `assert_awaited_once`, `assert_called_once_with` on parsers, URL construction verification for `get_price_history`.
- Minor observations:
  - `test_generic_4xx_raises_after_retries` docstring says "500 on all attempts raises RuntimeError from the if-branch" but the test name says "4xx". The status code 500 is a 5xx. This is cosmetic and does not affect test correctness.
  - `test_generic_4xx_retry_then_success` has the same naming inconsistency. Both test 5xx behavior via the `>= 400` branch in the source, which is technically correct but the name is misleading.
- No test smells (no overly broad mocks, no assertions on implementation details that would make tests brittle).

### `tests/unit/test_parsers_edge.py`
- Quality: HIGH
- Covers all previously uncovered branches: JSON-LD with non-dict (list), multiple LD blocks with first malformed, empty SKU, breadcrumb alternate name extraction, breadcrumb malformed JSON, breadcrumb non-dict, EN image URL heuristic, price snapshot with no offers/no price, history with no chart config, malformed JSON, invalid dates, series shorter than labels, set links with excluded slugs.
- Helper functions `_to_decimal`, `_parse_date`, `_extract_stat_price`, `_extract_tcg_price` all have edge case coverage.
- The result: `parsers/myp.py` at 100% coverage.
- Assertions are specific and verify exact values (Decimal amounts, None returns, list lengths).
- No issues found.

### `tests/unit/test_cli_collector.py`
- Quality: HIGH
- Tests all three collector commands (`backfill`, `update`, `retry-failed`) plus `_print_summary` edge cases and CLI help output.
- Uses `click.testing.CliRunner` correctly -- the standard approach for Click CLI testing.
- `_make_summary` factory function is clean and supports multiple test scenarios via keyword arguments.
- `_print_summary` edge cases covered: errors list, truncation at 20 with overflow message, no `finished_at`, elapsed time calculation.
- Minor observation: `test_backfill_with_options` (lines 87-118) has a dead code block (lines 92-95) where a `with patch` context manager does nothing because it only contains `pass`. The actual test continues below with a second `with patch` block. This is harmless but untidy -- it looks like a false start that was left in.
- Result: `cli/main.py` at 99%, only the `if __name__ == "__main__"` guard uncovered (expected).

### `docs/prd/F02-reproducibility-docs.md`
- Quality: HIGH
- Accurately describes the problem (no Makefile, no `.env.example`, incomplete `pyproject.toml`, no bootstrap scripts, missing docs).
- Goals align with what F02 actually delivered (Makefile, `.env.example`, bootstrap scripts, 11 doc files, ADR-0002, diagrams).
- Non-goals are reasonable.
- Acceptance criteria are specific and testable.

### `docs/prd/F03-analytics-engine.md`
- Quality: HIGH
- Problem statement correctly identifies the gap between raw price observations and actionable indicators.
- Technical analysis section accurately describes the pure-function architecture, Decimal arithmetic, and module structure.
- Goals match the delivered functionality (MA 7/30/90, ATH/ATL, volatility, momentum, CLI `analyze` subcommand).
- Acceptance criteria match the F03-README.md global ACs.

### `docs/prd/F04-collector-scaling.md`
- Quality: HIGH
- Problem statement accurately identifies the three bottlenecks (per-row INSERT, no concurrency, no resume).
- Technical analysis covers batch upsert (INSERT ON CONFLICT DO NOTHING), asyncio.Semaphore concurrency, and stateless resume via DB query.
- References the Gandalf retroactive review items (ACT-06, ACT-07, ACT-08) correctly.
- Non-goals are well-scoped (no distributed workers, no queue-based architecture).
- Acceptance criteria are specific and match what was delivered.

### `docs/diagrams/F04-architecture.mmd`
- Quality: HIGH
- Comprehensive flowchart covering CLI commands, collector orchestrator (resume logic, concurrent processing), MYP provider, and database layer (batch upsert with batch sizes).
- Accurately represents the actual code structure in `src/collectors/backfill.py` and `src/database/repository.py`.
- Shows the correct data flow: CLI -> orchestrator -> provider/database.
- Concurrency primitives (Semaphore, Lock, asyncio.gather) are correctly depicted.
- Batch upsert detail (batches of 500, INSERT ON CONFLICT DO NOTHING) matches the implementation.

### `docs/diagrams/F04-journey.mmd`
- Quality: HIGH
- BPMN-style user journey starting from `backfill --set slug --concurrency N`.
- Correctly shows the decision points: limit set?, resume enabled?, cards to process?, success/failure per card.
- Resume logic flow (query DB -> build set -> filter -> log) matches the implementation.
- Concurrency flow (create Semaphore -> acquire -> fetch -> release) is accurate.
- Error handling path (record error -> increment failed) correctly shown.

## Summary

F05 is a clean tech debt cleanup feature. All nine acceptance criteria are met, most with significant margin. Coverage jumped from 86% to 97.21%, with the three target files (`provider.py`, `parsers/myp.py`, `cli/main.py`) all reaching 99-100%. The new tests are well-structured with correct mock placement and strong assertions. The three retroactive PRDs accurately document what was delivered in F02, F03, and F04. The F04 diagrams faithfully represent the codebase architecture and user journey.

Two cosmetic issues noted (misleading test method names referencing "4xx" when testing 5xx status codes; dead code block in `test_backfill_with_options`). Neither affects correctness or test reliability, so they do not block approval.
