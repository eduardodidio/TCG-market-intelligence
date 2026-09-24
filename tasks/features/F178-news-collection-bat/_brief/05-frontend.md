# F178 — Component: NewsPage states

Files (owner F178-T05): `frontend/src/api/news.ts`,
`frontend/src/pages/NewsPage.tsx`, `frontend/src/pages/__tests__/NewsPage.test.tsx`,
`frontend/src/i18n/locales/en.json`, `frontend/src/i18n/locales/pt-BR.json`
(edit ONLY inside the existing `"news": {...}` block — other batch features edit
other blocks of these files).

## API client
```ts
export interface NewsStatus { total_items: number; last_fetched_at: string | null; newest_published_at: string | null; }
export function fetchNewsStatus(): Promise<ApiResponse<NewsStatus>> { return apiGet<NewsStatus>("/api/v1/news/status"); }
```

## States (mutually exclusive, in priority order)
1. **Loading** — existing `LoadingSpinner`.
2. **Error** — existing `ErrorBanner` with retry; title `news.errorTitle`.
   Status fetch failure must NOT block the list (status is optional chrome).
3. **No data collected** (`status.total_items === 0`) — `EmptyState` with
   `news.noDataTitle` / `news.noDataDescription`
   ("Ainda não há notícias coletadas. A coleta roda pela rotina `bats/fetch-news.bat`.").
   Hide filter tabs/category chips in this state (`data-testid="news-no-data"`).
4. **Filter empty** (`total_items > 0` but `items.length === 0`) —
   - filter `unread`: `news.allReadTitle` ("Você está em dia!") + button
     `news.showAll` that switches to the `all` tab (`data-testid="news-show-all"`).
   - other filter/category: `news.filterEmptyTitle` + button `news.clearFilters`
     (resets category to `all` and filter to `all`).
5. **List** — existing grid.

## Freshness line
Under the `<h1>`: `news.lastUpdated` ("Última coleta: {{date}}") using
`last_fetched_at` (`toLocaleString`). If older than 72 h, render it in amber
with `news.stale` suffix ("desatualizado") — `data-testid="news-stale"`.
Hide the line when status is unavailable.

## i18n keys to add (both locales, inside `"news"`)
`errorTitle, noDataTitle, noDataDescription, allReadTitle, allReadDescription,
showAll, filterEmptyTitle, clearFilters, lastUpdated, stale`.
Replace the now-misleading `emptyDescription` text (it tells users to "ask an admin to run fetch-news") — keep the key for compatibility.
