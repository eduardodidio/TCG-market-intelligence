# F178 — Notícias não carregam: coleta via rotina .bat

**Status:** planned

## Goal

Make the News page (F166) show news. The page is empty because `news_items`
is never populated: the only write path (`fetch-news` CLI) crashes on
`import feedparser` (never declared in `pyproject.toml`) and nothing schedules
it. F178 rewrites the fetcher with `httpx` + stdlib XML (no new dependency),
adds a dedicated CLI module with a `--check-sources` dry run, a local Windows
routine `bats/fetch-news.bat` that writes to Neon, a read-only
`GET /api/v1/news/status` endpoint, and clear empty/filter-empty/error/stale
states on `NewsPage`. The API stays read-only (no network I/O on Render).

Brief (sharded): `_brief/00-overview.md` (scope, constraints, AC),
`_brief/01-diagnosis.md` (root causes), `_brief/02-fetcher.md`,
`_brief/03-status-endpoint.md`, `_brief/04-cli-bat.md`,
`_brief/05-frontend.md`, `_brief/06-docs.md`.

## Architecture impact

| Layer | Change |
|---|---|
| Service | `src/services/news_fetcher.py` — feedparser → httpx + ElementTree; per-source report; `dry_run` |
| Repository | `Repository.get_news_status()` (1 new method, news section) |
| API | `GET /api/v1/news/status` in existing `news.py` router (no `app.py` change) |
| CLI | NEW `src/cli/news_cmd.py`; `main.py` loses inline `fetch-news`, gains 1 `add_command` line |
| Ops | NEW `bats/fetch-news.bat` |
| Frontend | `api/news.ts`, `NewsPage.tsx`, `news` block of `en.json` / `pt-BR.json` |
| DB schema | **none** (no `models.py` change) |
| Dependencies | **none added** (`httpx`, `click` already declared) |

## Waves

- **Wave 0**: F178-T01
- **Wave 1**: F178-T02, F178-T03, F178-T05, F178-T06
- **Wave 2**: F178-T04
- **Wave 3**: F178-T07
- **Wave 4**: F178-T08

## Tasks and files touched (for cross-feature overlap detection)

| Task | Wave | Type | Files touched | Shared high-risk? |
|---|---|---|---|---|
| F178-T01 | 0 | docs/setup | `docs/prd/F178-news-collection-bat.md` (new), `tests/fixtures/news/rss_sample.xml` (new), `tests/fixtures/news/atom_sample.xml` (new), `tests/fixtures/news/invalid.xml` (new) | no |
| F178-T02 | 1 | backend | `src/services/news_fetcher.py`, `tests/services/test_news_fetcher.py` | no |
| F178-T03 | 1 | backend | `src/database/repository.py` (news section only, +1 method), `src/api/routers/news.py`, `tests/api/test_news.py` | repository.py: low (append-only in F166 block) |
| F178-T05 | 1 | frontend | `frontend/src/api/news.ts`, `frontend/src/pages/NewsPage.tsx`, `frontend/src/pages/__tests__/NewsPage.test.tsx`, `frontend/src/i18n/locales/en.json` (`news` block only), `frontend/src/i18n/locales/pt-BR.json` (`news` block only) | locales: medium (block-scoped) |
| F178-T06 | 1 | docs | `docs/diagrams/F178-architecture.mmd` (new), `docs/diagrams/F178-journey.mmd` (new) | no |
| F178-T04 | 2 | backend | `src/cli/news_cmd.py` (new), `tests/cli/test_news_cmd.py` (new) | no |
| F178-T07 | 3 | infra/docs | `src/cli/main.py`, `bats/fetch-news.bat` (new), `README.md`, `docs/adr/<next>-news-collection-offline-bat.md` (new) | **YES** — main.py, bats/, README.md |
| F178-T08 | 4 | ops/test | `src/services/news_fetcher.py` (`SOURCES` list only), `docs/prd/F178-news-collection-bat.md` (validation log section) | no |

Files F178 explicitly does **not** touch: `src/api/app.py`,
`src/database/models.py`, `frontend/src/App.tsx`,
`frontend/src/components/Layout.tsx`, `pyproject.toml`.

## Contracts between parallel tasks

- `fetch_news(...)` return shape and `dry_run`/`client` kwargs — `_brief/02-fetcher.md` (T02 → T04).
- `GET /api/v1/news/status` payload — `_brief/03-status-endpoint.md` (T03 → T05; T05 mocks the API client in tests, so they run in parallel).

## Global acceptance criteria

1. `python -m src.cli.main fetch-news` works in an env **without** `feedparser`, populating `news_items` (idempotent on re-run).
2. `fetch-news --check-sources` prints a per-source table and writes nothing.
3. Exit code 1 when every source fails; 0 otherwise.
4. `bats/fetch-news.bat` exists and follows the `process-queue.bat` pattern.
5. `GET /api/v1/news/status` returns `{total_items, last_fetched_at, newest_published_at}`.
6. The news router imports no network/fetcher module (test-enforced).
7. NewsPage distinguishes: no data collected / all read / filter empty / error; shows last-collection time and stale (>72h) hint.
8. `pytest tests/ --cov=src` and `cd frontend && npm test` green; `ruff check src/` clean; `cd frontend && npm run build` OK.
9. PRD, ADR, both diagrams, README updated.
10. Default sources validated live on the user's machine (T08); broken ones removed.

## Gitflow / branch (Wave 0 checklist)

All work happens on **`homol`** (CLAUDE.md Gitflow). T01 confirms the
branch before anything is written; no task pushes to `main`. Stage files one
by one (never `git add -A`).

## Diagrams

- `docs/diagrams/F178-architecture.mmd` — owner F178-T06
- `docs/diagrams/F178-journey.mmd` — owner F178-T06

## Test impact (existing tests that change)

- `tests/services/test_news_fetcher.py` — every `@patch("src.services.news_fetcher.feedparser")` test must be rewritten to inject an `httpx.Client` with `httpx.MockTransport` (T02).
- `frontend/src/pages/__tests__/NewsPage.test.tsx` — the API mock must add `fetchNewsStatus`; the old "No news yet" empty test changes to the no-data state (T05).
- CLI: there is no existing test for `fetch-news`; T04 adds one.

## ADR number (batch reservation)
This feature's ADR number is **0019**, reserved in `tasks/features/EXECUTION-PLAN-F171-F179.md`. It overrides any "next free number" instruction in the task files.
