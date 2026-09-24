# F178 — Component: documentation

- PRD: `docs/prd/F178-news-collection-bat.md` (T01) — follow `docs/prd/template.md`.
  Include the diagnosis table from `_brief/01-diagnosis.md`.
- ADR: `docs/adr/<next-free-number>-news-collection-offline-bat.md` (T07). Compute
  the number at execution time (`ls docs/adr | sort | tail -1`) — other batch
  features may have taken 0014. Decision: collection runs locally via `.bat`
  writing to Neon; API is read-only; feedparser replaced by httpx + stdlib XML
  (no new dependency). Alternatives rejected: APScheduler job on Render
  (free tier sleeps, egress blocked/unreliable, blocks request workers);
  declaring feedparser (new dependency, no timeout/UA control).
- Diagrams (T06): `docs/diagrams/F178-architecture.mmd` and
  `docs/diagrams/F178-journey.mmd` (templates in `docs/diagrams/templates/`).
- README (T07): add under the news / routines section:
  `bats/fetch-news.bat`, `fetch-news --check-sources`, `GET /api/v1/news/status`,
  `NEWS_FEED_SOURCES` env override, new NewsPage states.
