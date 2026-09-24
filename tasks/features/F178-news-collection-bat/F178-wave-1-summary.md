# F178 — Wave 1 summary

**Status:** completed
**Tasks:** F178-T02, F178-T03, F178-T05, F178-T06
**Generated:** 2026-09-24T10:45:00Z

## Files touched
- `src/services/news_fetcher.py` (T02: replaced feedparser with httpx + stdlib ElementTree, per-source report, `dry_run`)
- `tests/services/test_news_fetcher.py` (T02: rewritten to inject `httpx.MockTransport` instead of `@patch(...feedparser)`)
- `src/database/repository.py` (T03: added `get_news_status()` aggregate query, news section only)
- `src/api/routers/news.py` (T03: added `GET /news/status` returning `{total_items, last_fetched_at, newest_published_at}`)
- `tests/api/test_news.py` (T03: status endpoint tests + assertion that router imports no fetcher/network module)
- `frontend/src/api/news.ts` (T05: added `NewsStatus` interface + `fetchNewsStatus()`)
- `frontend/src/pages/NewsPage.tsx` (T05: state matrix — no-data / all-read / filter-empty / error / stale(>72h) — plus last-collection line)
- `frontend/src/pages/__tests__/NewsPage.test.tsx` (T05: mocks `fetchNewsStatus`, old "No news yet" test replaced with no-data-state test)
- `frontend/src/i18n/locales/en.json`, `frontend/src/i18n/locales/pt-BR.json` (T05: `news` block only)
- `docs/diagrams/F178-architecture.mmd`, `docs/diagrams/F178-journey.mmd` (T06: new, component/data-flow + BPMN-style user journey)

## Decisions
- _none_ — implementation followed the sharded briefs (`02-fetcher.md`, `03-status-endpoint.md`, `05-frontend.md`) as written.

## Verification run this Wave
- `pytest tests/services/test_news_fetcher.py tests/api/test_news.py -q` → 62 passed (coverage gate failure is expected/global, not scoped to these files — `news_fetcher.py` itself at 92% line coverage).
- `ruff check src/services/news_fetcher.py src/api/routers/news.py src/database/repository.py` → clean.
- `cd frontend && npx vitest run src/pages/__tests__/NewsPage.test.tsx` → 16 passed (harmless `act()` warnings only).

## Notes for next Wave
- Wave 2 (T04, the CLI) depends on `fetch_news(...)`'s `dry_run`/`client` kwargs contract from T02 — confirmed present in `news_fetcher.py` as delivered this Wave.
- All Wave 1 file changes are **uncommitted** on the working tree (current branch: `claude/stoic-mccarthy-nv2690`, not `homol` — flag this to the user/Architect before committing, per CLAUDE.md Gitflow).
- Task file front-matter for T02, T05, T06 still reads `Status: planned` despite work being done and verified — only T03's header was updated to `done`; whoever runs Wave 2 should reconcile these headers first.
- T07 (Wave 3) still needs `main.py`/`bats/`/`README.md` — none of that was touched this Wave, as planned.

DIDIO_DONE: techlead wrote F178-wave-1-summary.md
