# F178 Test Plan

**Status:** drafted
**Generator:** TEA
**Generated at:** 2026-09-24
**Source brief:** F178 — Notícias não carregam: coleta via rotina .bat (fetcher rewrite httpx+stdlib XML, `fetch-news` CLI, `bats/fetch-news.bat`, `GET /api/v1/news/status`, NewsPage empty/error/stale states)

---

## 1. Fixtures

| Fixture | Path | Domain | Owner |
|---------|------|--------|-------|
| `rss_sample.xml` | `tests/fixtures/news/rss_sample.xml` | feed-parsing | F178-T01 |
| `atom_sample.xml` | `tests/fixtures/news/atom_sample.xml` | feed-parsing | F178-T01 |
| `invalid.xml` | `tests/fixtures/news/invalid.xml` | feed-parsing | F178-T01 |
| `httpx.MockTransport` handler (per-source status/body map) | `tests/services/test_news_fetcher.py` (inline) | http | F178-T02 |
| SQLite tmp repo (`Repository(db_url="sqlite:///" + tmp_path/"t.db")`) | `tests/services/test_news_fetcher.py`, `tests/cli/test_news_cmd.py` (existing pattern) | db | F178-T02 |
| `test_news.py` FastAPI app + `dependency_overrides` (`get_current_user`, `get_db`) | `tests/api/test_news.py` (existing) | api | F178-T03 |
| `CliRunner` invoking `fetch_news_command` with patched `src.services.news_fetcher.fetch_news` | `tests/cli/test_news_cmd.py` | cli | F178-T04 |
| `NewsPage.test.tsx` mocks (`../../api/news` incl. `fetchNewsStatus`, `react-i18next`) | `frontend/src/pages/__tests__/NewsPage.test.tsx` (existing, extended) | frontend | F178-T05 |
| `vi.useFakeTimers`/`vi.setSystemTime` for 72h stale boundary | `frontend/src/pages/__tests__/NewsPage.test.tsx` (inline) | frontend/time | F178-T05 |

All fixtures reused across ≥2 test cases in the same file (RSS/Atom fixtures alone drive ~10 scenarios each in T02; the MockTransport handler is reused per-source in every error-path test). No new fixture proposed beyond what T01–T05 already declare — nothing added "for completeness."

## 2. Harnesses por fronteira

### Unit

- **Framework:** pytest
- **Command:** `pytest tests/ -q`
- **Default path:** `tests/services/test_news_fetcher.py`, `tests/cli/test_news_cmd.py`, `tests/database/test_repository.py` (news section)

### Integration

- **Framework:** pytest + FastAPI `TestClient` (in-process ASGI, no real server)
- **Command:** `pytest tests/api/test_news.py -q`
- **Default path:** `tests/api/test_news.py`

### E2E

**N/A** — no browser/Playwright E2E for this feature. The `.bat` routine and live feed validation (F178-T08) run manually on the user's Windows machine against real feeds; this is explicitly a manual/live step (AC9/AC10), not an automated E2E suite, because the cloud sandbox blocks outbound HTTP to feed hosts and Windows Task Scheduler is not CI-reachable. Frontend coverage stops at Vitest component tests (`frontend/src/pages/__tests__/NewsPage.test.tsx`) with the API layer mocked.

## 3. Perf budgets

_Sem perf budgets aplicáveis._ The fetcher runs offline on a user-triggered cron (`bats/fetch-news.bat`), not in the Render request path (AC6 — the news router never does network I/O), so there is no user-facing latency SLA. The one numeric guard in scope (5 MB body cap in `news_fetcher.py`, `_brief/02-fetcher.md`) is a correctness/safety bound, not a perf budget, and is covered as a test scenario (§5, "payload > 5 MB").

## 4. Mocks vs hits real

| Componente | Decisão | Justificativa |
|-----------|---------|---------------|
| RSS/Atom HTTP feeds (`fetch_feed`) | mock | `httpx.Client(transport=httpx.MockTransport(handler))` — real feeds are non-deterministic, rate-limited, and unreachable from CI/sandbox (proxy blocks egress). No new dependency needed; httpx ships `MockTransport`. |
| `xml.etree.ElementTree` parsing (`parse_feed`) | real | Pure stdlib parsing over fixture bytes — deterministic, fast, and the actual behavior under test (per `feedback_no_ceremony_specs.md`, mocking the parser would hide real bugs). |
| SQLite repository (`Repository.upsert_news_item`, `get_news_status`) | real | In-memory/tmp-file SQLite is fast and deterministic; mocking the repo would hide dedupe/aggregate-query bugs, which are exactly what T02/T03 need to verify. |
| FastAPI `TestClient` for `/news/status` | real | Runs the full ASGI stack in-process, no external dependency, matches existing `test_news.py` pattern. |
| `Repository` construction in CLI dry-run test | real object, asserted **not called** | T04 patches/spies on `Repository.__init__` (or the module-level import) to prove `--check-sources` never opens a DB connection — this is a behavior assertion, not a mock-for-speed decision. |
| Frontend `fetchNews` / `fetchNewsStatus` API client | mock | `vi.mock("../../api/news")` — Vitest cannot reach a real backend; existing NewsPage tests already mock this module. |
| `Date.now()` / current time (stale-threshold check) | mock | `vi.useFakeTimers()` / `vi.setSystemTime()` required for deterministic 71h-vs-73h boundary assertions. |
| Live feed hosts (Wizards, Scryfall, MTGGoldfish, EDHREC, HotC) | real, manual only | F178-T08 is an explicit live/manual step run by the user on their machine — not part of the automated suite, since these hosts are unreachable from the sandbox and non-deterministic. |

## 5. Test scenarios resumo

### Fixtures validity (F178-T01)

1. `rss_sample.xml` and `atom_sample.xml` parse successfully with `xml.etree.ElementTree.parse` (F178-T01)
2. `invalid.xml` raises `xml.etree.ElementTree.ParseError` (F178-T01)
3. RSS fixture covers: `enclosure[@url]`, `media:content[@url]`, `media:thumbnail[@url]`, `content:encoded` fallback, item with missing `link`, unparseable `pubDate`, non-UTC `pubDate` offset (F178-T01)
4. Atom fixture covers: entry with `rel="alternate"` link + `<summary>` + `<published>`; entry with unqualified `href` + `<content>` + only `<updated>`; entry where `alternate` must be preferred over `self` (F178-T01)

### Backend — news fetcher (F178-T02)

5. `parse_feed` on RSS fixture returns entries for items A/B/C, skips nothing at parse time (D kept with empty link, filtered later) (F178-T02)
6. `fetch_news` on RSS fixture stores 3 items (A, B, C), skips D (missing link) → `skipped == 1` (F178-T02)
7. Category `ban` assigned to item A (title contains "banned") (F178-T02)
8. Image extraction precedence: `enclosure` (item A), `media:content` (item B), `media:thumbnail` (item C) (F178-T02)
9. `parse_feed` on Atom fixture returns 3 entries; alternate link preferred over self-link entry (F178-T02)
10. `fetch_news` on Atom fixture stores 3 items (F178-T02)
11. Idempotency: running `fetch_news` twice on the same fixture → second run `new == 0`, `skipped == N` (dedupe by `source_url`) (F178-T02)
12. Date handling: `+0000` and `-0300` `pubDate` offsets both stored as naive UTC; unparseable `pubDate` ("sometime soon") → `published_at is None`; Atom `updated` used when `published` absent (F178-T02)
13. HTTP 403 on one source → that source `ok=False, http_status=403`; other sources still processed and stored (F178-T02)
14. `httpx.TimeoutException` on one source → `ok=False, http_status=None, error` set; other sources unaffected (F178-T02)
15. Invalid XML body → `FeedParseError` captured as a per-source error, not raised to the caller; other sources still processed (F178-T02)
16. Boundary: `max_per_source=1` caps stored entries per source (F178-T02)
17. Boundary: response body > 5 MB → treated as source error `"payload too large"`, not parsed (F178-T02)
18. Boundary: empty `<channel>` (0 items) → `ok=True, entries=0` (F178-T02)
19. `load_sources()`: `NEWS_FEED_SOURCES` env with 2 valid `Name|url` pairs → both parsed; one malformed pair among valid ones → malformed skipped, valid ones kept; env unset/empty → falls back to default `SOURCES` (F178-T02)
20. `dry_run=True`: `repo=None` accepted, `sources[*].entries` populated, `repo.upsert_news_item` never called (assert not-called on a spy, or assert DB row count unchanged) (F178-T02)
21. Coverage of `src/services/news_fetcher.py` ≥ 90% (line, via `--cov-report=term-missing`) (F178-T02)

### Backend — `/news/status` endpoint (F178-T03)

22. Empty DB → `{"total_items": 0, "last_fetched_at": null, "newest_published_at": null}` (F178-T03)
23. Populated DB with 3 items with distinct `fetched_at`/`published_at` → `total_items == 3`, `last_fetched_at`/`newest_published_at` equal the max of each column (F178-T03)
24. Edge: all `published_at` NULL across rows → `newest_published_at is null`, `total_items` still correct (F178-T03)
25. Boundary: exactly 1 item in DB → correct single-row aggregate (F178-T03)
26. Unauthenticated request to `/news/status` → rejected the same way as other news endpoints (401/403 per existing pattern) (F178-T03)
27. Static-source guard (AC6): reading `src/api/routers/news.py` source text contains no `news_fetcher`, `httpx`, `feedparser`, or `requests` import (F178-T03)
28. Regression: `GET /news/unread-count` still resolves correctly — new `/status` route does not shadow or reorder existing routes (F178-T03)
29. Regression: all existing tests in `tests/api/test_news.py` still pass unmodified (F178-T03)

### Backend — CLI `fetch-news` (F178-T04)

30. `python -c "from src.cli.news_cmd import fetch_news_command"` succeeds without importing `src.cli.main` (no circular import) (F178-T04)
31. Mixed sources (1 ok, 1 fail) → exit code 0; both `[OK]`/`[FAIL]` lines printed; summary numbers (fetched/new/skipped/errors) match the fetcher's return dict (F178-T04)
32. All sources fail → exit code 1, all lines show `[FAIL]` (F178-T04)
33. `--check-sources` → `fetch_news` invoked with `dry_run=True, repo=None`; `Repository` never constructed (patched/spied and asserted not-called) (F178-T04)
34. `--source mtggoldfish` (case-insensitive) filters to that source only; unknown source name → `click.UsageError`, exit code 2 (F178-T04)
35. Boundary: `--max-per-source 0` rejected by `click.IntRange(1, 200)`; `--max-per-source 200` accepted (F178-T04)
36. `--db sqlite:///...` explicit URL takes precedence over `_resolve_db` auto-detection (F178-T04)
37. Coverage of `src/cli/news_cmd.py` ≥ 90% (F178-T04)

### Backend — shared-file wiring (F178-T07)

38. `test_registered_in_main_cli`: `CliRunner().invoke(cli, ["fetch-news", "--help"])` exits 0 and output contains `--check-sources` (F178-T07)
39. `list(cli.commands).count("fetch-news") == 1` — no duplicate registration from the deleted inline command (F178-T07)
40. `python -c "import src.cli.main"` succeeds — no circular import introduced by the new `from src.cli.news_cmd import fetch_news_command` line (F178-T07)
41. `bats/fetch-news.bat` file content contains `cd /d "%~dp0\.."` and `python -m src.cli.main fetch-news`, and the `[FAIL]` branch guarded by `if errorlevel 1` (static content check — Windows itself is not run in CI) (F178-T07)
42. Regression: `python -m src.cli.main --help` still exits 0 and lists all other existing commands (F178-T07)

### Frontend — NewsPage states (F178-T05)

43. No-data state: `fetchNewsStatus` resolves `total_items: 0`, list empty → `data-testid="news-no-data"` renders, filter tabs/category chips hidden (F178-T05)
44. All-read state: `total_items: 5`, `unread` filter returns empty list → `data-testid="news-all-read"`; clicking `news-show-all` switches to `all` tab and re-invokes `fetchNews` with `filter: "all"` (F178-T05)
45. Filter-empty state (non-unread): category `ban` returns empty list with `total_items > 0` → `data-testid="news-filter-empty"`; clicking clear-filters resets category to `""`/filter to `all` (F178-T05)
46. Error state: `fetchNews` rejects → `ErrorBanner` shown with `news.errorTitle`; retry button re-invokes the fetch (F178-T05)
47. Status-fetch-failure isolation: `fetchNewsStatus` rejects while `fetchNews` succeeds with items → grid renders normally, no error banner, no freshness line shown (F178-T05)
48. Stale boundary: `last_fetched_at` set to 71h before fake-timer "now" → `data-testid="news-stale"` absent; set to 73h before → `news-stale` present (F178-T05)
49. Freshness line (`data-testid="news-last-updated"`) renders `last_fetched_at` via `toLocaleString` when status available; hidden when status unavailable (F178-T05)
50. Regression: existing grid/pagination/mark-read/mark-unread tests in `NewsPage.test.tsx` still pass after the mock additions (F178-T05)
51. `cd frontend && npm test` and `npm run build` pass with no TypeScript errors (F178-T05)

### Diagrams (F178-T06)

52. `docs/diagrams/F178-architecture.mmd` and `docs/diagrams/F178-journey.mmd` exist and are syntactically valid Mermaid (balanced `subgraph`/`end`, valid diagram-type first line, no unescaped quotes in labels) — manual/visual review, no automated test (F178-T06)

### Live validation (F178-T08, manual/non-CI)

53. `fetch-news --check-sources` run by the user against real feeds → every remaining default source reports `ok=True, entries > 0`; results appended to the PRD "Live validation log" (F178-T08)
54. After the user runs `bats\fetch-news.bat` once against Neon: `GET /api/v1/news/status` reports `total_items > 0`; running the `.bat` again is idempotent (`new == 0` on the CLI's printed summary) (F178-T08)
55. Regression: `pytest tests/services/test_news_fetcher.py tests/cli/test_news_cmd.py tests/api/test_news.py -q` stays green after any `SOURCES` edits (F178-T08)

## 6. Anotações para tasks

| Task | Fixtures |
|------|----------|
| F178-T02 | `rss_sample.xml`, `atom_sample.xml`, `invalid.xml`, `httpx.MockTransport` handler, SQLite tmp repo |
| F178-T03 | `test_news.py` FastAPI app + `dependency_overrides` |
| F178-T04 | `CliRunner` + patched `fetch_news`, SQLite tmp repo (not-constructed assertion) |
| F178-T05 | `NewsPage.test.tsx` API mocks (incl. `fetchNewsStatus`), `vi.useFakeTimers`/`vi.setSystemTime` |
| F178-T07 | `CliRunner` (reuses F178-T04's file), static `.bat` content check |
| F178-T08 | live feed hosts (manual, non-CI), reuses F178-T02/T04/T03 automated suites for regression |

## Risks for QA

- **Live source drift (AC9/AC10, F178-T08):** the default `SOURCES` list is a planning-time guess; QA should not assume the 5 listed feeds are still correct at execution time — verify against the PRD's "Live validation log" section, not the brief.
- **Route-order regression (F178-T03):** the new `GET /status` route sits among several `GET`/`POST /{news_id}/...` routes in the same router; QA should specifically re-check `/news/unread-count` and any other `/{news_id}` path still resolves correctly after `T07`'s edits, since path-matching order bugs are easy to introduce silently.
