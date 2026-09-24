# F178 — Wave 3 summary

**Status:** completed
**Tasks:** F178-T07
**Generated:** 2026-09-24T11:05:00Z

## Files touched
- `src/cli/main.py` (T07: removed inline `fetch-news` command block; added
  `from src.cli.news_cmd import fetch_news_command` + `cli.add_command(...)`
  right before `if __name__ == "__main__":`)
- `bats/fetch-news.bat` (T07: new, follows `process-queue.bat` pattern —
  `cd /d "%~dp0\.."`, calls `python -m src.cli.main fetch-news
  --max-per-source 30`, `[FAIL]`/`[DONE]` branches on `errorlevel`)
- `README.md` (T07: new "F178 -- News Collection via Offline Routine"
  section documenting the fetcher rewrite, CLI flags, `.bat` routine,
  `/api/v1/news/status`, `NEWS_FEED_SOURCES`, and NewsPage states; links
  ADR-0019)
- `docs/adr/0019-news-collection-offline-bat.md` (T07: new, reserved number
  0019 per `EXECUTION-PLAN-F171-F179.md`)
- `tests/cli/test_news_cmd.py` (T07: added `TestRegisteredInMainCli` —
  asserts `fetch-news --help` exits 0, shows `--check-sources`, and
  `cli.commands` contains `fetch-news` exactly once)

## Decisions
- No deviation from the brief: single `add_command` line, old inline block
  fully removed (no dual registration).

## Notes for next Wave
- Verified locally: `python -m src.cli.main --help` lists `fetch-news`
  exactly once; `pytest tests/cli/test_news_cmd.py -q` → 10/10 passed;
  `ruff check src/cli/main.py src/cli/news_cmd.py` clean.
- Note for whoever runs pytest/ruff next: the repo's global `python`/`uv`
  tool environments lack `click` — use `/usr/local/bin/python3 -m pytest`
  (or the project's normal venv, if one is activated) instead of a bare
  `uv run pytest`.
- README.md, src/cli/main.py, tests/cli/test_news_cmd.py, and
  docs/adr/0019-*.md are still uncommitted (working tree) as of this
  summary — Wave 4 (F178-T08) should stage and commit Wave 3's files
  file-by-file before adding its own SOURCES-list change, per the
  "no `git add -A`" guardrail.
