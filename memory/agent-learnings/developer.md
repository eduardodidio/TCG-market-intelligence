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
