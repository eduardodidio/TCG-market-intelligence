# F178 — Wave 4 summary

**Status:** partial (escalated to user)
**Tasks:** F178-T08
**Generated:** 2026-09-24T11:15:00Z

## Files touched
- `docs/prd/F178-news-collection-bat.md` (T08: replaced the empty "Live
  validation log" placeholder with a dated entry recording the
  `--check-sources` attempt and a request for the user to re-run it
  locally)

## Decisions
- `src/services/news_fetcher.py` `SOURCES` list was **not** edited — the
  task's own Dev Notes require stopping and asking the user when the
  sandbox proxy blocks outbound feed requests, rather than guessing at
  replacement URLs.

## Notes for next Wave
- All 5 default sources failed with a proxy `CONNECT` 403 (confirmed via
  raw `curl` to `scryfall.com`, same 403 at the tunnel level) — this is the
  cloud sandbox's outbound restriction, not the feeds themselves failing,
  so it is **not** evidence any source is broken.
- **Blocking item for the user:** run
  `python -m src.cli.main fetch-news --check-sources` locally (outside the
  sandbox) and share the per-source table. Only then can `SOURCES` be
  pruned/fixed (candidates already noted in the PRD: Scryfall
  `/blog/rss` as a fallback for `/blog/feed.atom`; drop Wizards News if it
  has no working RSS, no HTML scraping).
- After the user confirms `SOURCES`, the remaining T08 acceptance
  criteria still need action: run `bats\fetch-news.bat` against Neon
  (write access — requires explicit user confirmation per CLAUDE.md), then
  verify `GET /api/v1/news/status` shows `total_items > 0` and the News
  page renders the grid.
- No test/source-code changes this wave, so
  `pytest tests/services/test_news_fetcher.py tests/cli/test_news_cmd.py`
  and `ruff check src/` are unaffected (still green per Wave 3 notes).
- Working tree otherwise clean of feature files — only the PRD edit above
  is uncommitted; Wave 3's commits (CLI registration, `.bat`, README, ADR)
  are already on `homol`.
