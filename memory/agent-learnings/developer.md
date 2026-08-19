# Developer Learnings

(QA appends to this file at the end of every feature retrospective.
Each entry is a lesson that generalizes beyond a single bug.)

## F01 -- MYP Cards Backfill (2026-08-18)

- **Use `curl_cffi` with `impersonate="chrome"` for Cloudflare-protected sites.** `httpx` and `requests` get 403 from MYP Cards. This is a hard requirement — do not attempt other HTTP libraries without testing Cloudflare bypass first.
- **Design for idempotency from day one.** The upsert pattern with unique constraints on `(external_id, source, observed_at)` ensured re-running backfill inserts 0 duplicates. Always add unique constraints before the first data load, not after.
- **Include a data validation task after any bulk data operation.** F01-T02's SQL queries (card count, observation count, date range, encoding check) caught issues that unit tests alone would not have revealed. Make this a standard pattern.

## F02 -- Reproducibility & Living Documentation (2026-08-18)

- **Verify actual filenames on disk before writing cross-links.** Three broken links shipped because the developer used assumed filenames from the task spec instead of checking what earlier waves actually created (e.g., `0002-web-stack-fastapi.md` vs `0002-web-stack-decision.md`). A quick `ls` after writing cross-links catches this class of bug.
- **For docs in the same directory, use bare filenames.** Relative paths like `./adr/` or `../CONTRIBUTING.md` are error-prone when source and target live in the same `docs/` folder. Always use `ARCHITECTURE.md`, not `./ARCHITECTURE.md`.

## F03 -- Analytics Engine (2026-08-18)

- **Move all imports to the top of the file.** Inline `from datetime import timedelta` inside function bodies (indicators.py:117, 171) works but is inconsistent with the rest of the codebase. Top-level imports are easier to audit and follow PEP 8.
- **Add explicit tests for division-by-zero guards.** The `past_price == 0` guard in `compute_momentum` is correct but untested. When writing a guard clause, immediately write the test -- it serves as documentation of intent and prevents future regressions if the guard is accidentally removed.

## F05 -- Technical Debt Cleanup (2026-08-18)

- **Run `ruff check` on every new file before declaring a task done.** F05 introduced 6 lint violations across 3 new test files (unused imports, unsorted imports, line too long). Pre-commit hooks would catch these at commit time, but running lint during development avoids rework and keeps the QA pass clean.
- **Name test methods accurately for the behavior they test.** Two test methods named `test_generic_4xx_*` actually tested 5xx status codes. Misleading names erode trust in test suites -- future readers will question whether the test is wrong or the name is wrong.
- **Remove dead code blocks from tests.** A `with patch(...) as mock_bf: pass` block in `test_backfill_with_options` does nothing and triggers an F841 lint violation. If a mock setup is not needed, delete it rather than leaving an empty block.

## F07 -- Front-end Dashboard (2026-08-18)

- **Include coverage tooling in Wave 0 scaffolding.** `@vitest/coverage-v8` was missing from devDependencies, forcing QA to install it. Always add the coverage provider alongside the test framework in the initial project setup.
- **Do not export constants that have no consumer.** `PERIOD_OPTIONS` in constants.ts was exported but never imported -- dead code that confuses future developers about project conventions. If a constant is only used locally, keep it local.
- **Do not configure features you do not use.** The `@/` path alias was configured in both tsconfig.json and vite.config.ts but no import in the codebase used it. Unused configuration signals intent without follow-through and creates confusion about project conventions.

## F08 -- Data Enrichment (2026-08-19)

- **When a test plan exists with numbered cases, implement all of them.** F08's test plan had 18 unit test cases (U-01 through U-18). The developer shipped 15, missing U-04, U-11, and U-16. QA had to fill those gaps. Treat test plan IDs as a checklist -- mark each one off as you implement it.
- **Always test default parameter values with URL assertions.** Changing a UI default (e.g., movers period from 7d to 30d) must have a corresponding test that asserts the fetch URL contains the new default. Component rendering tests alone do not catch regressions to the default value.
