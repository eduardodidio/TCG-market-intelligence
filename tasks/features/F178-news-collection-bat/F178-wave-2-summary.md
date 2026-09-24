# F178 — Wave 2 summary

**Status:** completed
**Tasks:** F178-T04
**Generated:** 2026-09-24T10:50:00Z

## Files touched
- `src/cli/news_cmd.py` (T04: new standalone `fetch-news` click command)
- `tests/cli/test_news_cmd.py` (T04: CliRunner tests, 9 scenarios)

## Decisions
- `_resolve_db` callback duplicated verbatim from `src.cli.main` (not imported)
  to avoid a circular import once T07 wires this command into `main.py` via
  `add_command`.
- `--check-sources` calls `fetch_news(None, dry_run=True, ...)` without ever
  constructing `Repository` — enforced in tests by patching `Repository` and
  asserting it's not called.

## Notes for next Wave
- T07 (Wave 3) must add exactly one line to `src/cli/main.py`:
  `cli.add_command(fetch_news_command)`, importing from `src.cli.news_cmd`.
  It must also remove the old inline `fetch-news` command from `main.py` —
  do not leave both registered.
- `src/cli/news_cmd.py` and `tests/cli/test_news_cmd.py` are new/untracked in
  git as of this Wave — T07 (or whoever commits Wave 2) should stage them
  file-by-file before the Wave 3 commit.
- 9/9 tests pass; `ruff check src/cli/news_cmd.py` is clean. The suite-wide
  coverage gate (70%) still fails, but only because most of `src/` is
  untouched by this run — not a regression from T04.
