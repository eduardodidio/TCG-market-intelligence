# ADR-0019: News Collection via Offline .bat Routine

## Status
Accepted

## Context
The News page (`frontend/src/pages/NewsPage.tsx`, F166) always showed the
empty state: `GET /api/v1/news` only reads the `news_items` table, and
nothing ever populated it. The existing `fetch-news` CLI command was
broken at import time because it depended on `feedparser`, which was
never declared in `pyproject.toml`. The configured feed URLs were also
unvalidated since F166 (one pointed at a pre-2023 Wizards RSS endpoint
that no longer exists).

The app runs on Render's free tier, where outbound egress from request
workers is unreliable and the dyno sleeps after inactivity, and other
local routines (`process-price-requests`, price snapshots) already run
as Windows `.bat` files scheduled via Task Scheduler on the operator's
machine, writing directly to the shared Neon database via `DATABASE_URL`.

## Decision
- Rewrite `src/services/news_fetcher.py` to use `httpx` (already a
  dependency) plus the stdlib `xml.etree.ElementTree` for RSS/Atom
  parsing, removing the undeclared `feedparser` dependency entirely.
- Add a standalone `fetch-news` CLI command (`src/cli/news_cmd.py`,
  registered into `src/cli/main.py` via `cli.add_command`) with a
  `--check-sources` dry-run mode and per-source `--source` filtering.
- Ship `bats/fetch-news.bat`, matching the structure of
  `bats/process-queue.bat`, so the operator collects news locally and
  writes straight to Neon — no server-side scraping.
- Keep the API layer (`GET /api/v1/news`, new `GET /api/v1/news/status`)
  strictly read-only; it never triggers network calls.

## Alternatives rejected
- **APScheduler job on Render:** the free-tier dyno sleeps and has
  unreliable/blocked egress to external feed hosts, and a scheduled job
  would compete with request-handling workers for the same process.
- **Declaring `feedparser` as a dependency:** would fix the immediate
  crash but adds a new dependency the project doesn't otherwise need,
  and it offers less control over timeouts and the User-Agent header
  than a direct `httpx` + stdlib XML implementation.

## Consequences
- News freshness depends on the operator running `bats/fetch-news.bat`
  (or the underlying CLI command) locally; there is no automatic
  server-side refresh. `GET /api/v1/news/status` lets the UI surface
  staleness so this limitation is visible rather than silent.
- No new dependencies were introduced.
- If sources go offline or change their feed format, `--check-sources`
  gives the operator a fast per-source diagnostic without touching the
  database.
