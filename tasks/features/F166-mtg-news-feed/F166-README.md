# F166 — MTG News Feed (Beta)

**Status:** planned
**Wave:** 0 (parallel with F164, F165, F167)
**Tasks:** 6
**Files touched:** `src/database/models.py`, `src/database/repository.py`, new `src/api/routers/news.py`, new `src/services/news_fetcher.py`, `src/cli/main.py`, `src/api/app.py`, new `frontend/src/pages/NewsPage.tsx`, `frontend/src/components/Layout.tsx`, `frontend/src/App.tsx`, `frontend/src/i18n/`, `bats/fetch-news.bat`, tests

## Summary

Create a news feed area for MTG updates (card releases, new collections, ban announcements, event dates). A bat script fetches news from reliable sources (MTG official RSS, Scryfall blog) and stores in the DB. Frontend shows news cards with read/unread filter. Feature is beta-gated.

## Tasks

| Task | Description | Wave |
|------|-------------|------|
| F166-T01 | DB models: news_items + user_news_reads tables | 0 |
| F166-T02 | News fetcher service + CLI command + bat script | 0 |
| F166-T03 | API router: list news, mark read/unread | 0 |
| F166-T04 | Frontend: NewsPage with read/unread filter | 0 |
| F166-T05 | Sidebar nav + route + i18n | 0 |
| F166-T06 | Tests (backend + frontend) | 0 |

## Architecture Notes

- **New dependency**: `feedparser` for RSS parsing — needs user confirmation
- Tables use same patterns as existing models (Integer PK, created_at timestamps)
- News fetcher is idempotent (dedup by source_url)
- Bat script is manual-run only (user decides when to fetch)
- Beta-gated via BetaRoute wrapper
- Unread badge count in sidebar nav item (optional enhancement)
