# TCG Market Intelligence

Historical price data collector for trading card games, starting with
**Magic: The Gathering** on the Brazilian market (MYP Cards).

## Clone to Run

```bash
git clone https://github.com/eduardodidio/tcg-market-intelligence.git
cd tcg-market-intelligence

# Mac
./bin/bootstrap-mac.sh

# Linux
./bin/bootstrap-linux.sh

# Or manually
make setup
make test
make run-backfill SET=dominaria-remastered LIMIT=5
```

## What it does

- Discovers all Magic cards available on MYP Cards (~48 pages of sets)
- Collects current prices (min, average, TCG Player reference)
- Collects historical price data (up to 3 years, weekly resolution)
- Stores everything in SQLite with full idempotency (no duplicate observations)
- Handles errors gracefully — failed cards are logged and can be retried
- Architecture supports adding new sources (Liga Magic, Scryfall, etc.)
- Computes analytics indicators: moving averages, ATH/ATL, volatility, momentum

## Quick Start

```bash
# Install dependencies and create virtual environment
make setup

# Run tests to verify everything works
make test

# Dry run — test with 5 cards, no database writes
make run-backfill SET=dominaria-remastered LIMIT=5 DRY_RUN=1

# Real backfill — collect a specific set
make run-backfill SET=dominaria-remastered

# Incremental update — fetch recent data for known cards
make run-update

# Retry failed cards
python -m src.cli.main retry-failed
```

## Commands

| Command | Description |
|---------|-------------|
| `backfill` | Full collection: discover cards + fetch all history |
| `update` | Incremental: fetch recent data for known cards only |
| `retry-failed` | Reprocess previously failed cards |
| `snapshot-prices` | Daily price snapshot from JSON-LD on product pages |
| `scan` | Trigger a collection price scan with optional filters |
| `scan-history` | List past scan runs with metrics |
| `update-exchange-rate` | Fetch USD/BRL exchange rate from BCB PTAX |
| `schedule-list` | List scheduled scans (filter by `--status`) |
| `schedule-add` | Create a scheduled scan (name, cron, type) |
| `schedule-remove` | Remove a scheduled scan by ID |
| `analyze list` | List all cards with observation counts |
| `analyze card <id>` | Compute analytics for a single card by external ID |

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--db` | `sqlite:///tcg_market.db` | Database connection string |
| `--set` | all sets | Only collect from this set slug |
| `--limit` | unlimited | Max cards to process |
| `--dry-run` | off | Don't write to database |
| `--delay` | 1.0 | Seconds between requests |
| `--history-days` | 1095 | Days of price history to fetch |
| `--concurrency` | 3 | Max concurrent cards during backfill |
| `--no-resume` | off | Re-process all cards (skip resume logic) |
| `--source` | `myp` | Data source (for analyze commands) |
| `--price-field` | `median_price` | Price field to analyze (for analyze card) |

## Project Structure

```
src/
  domain/          Domain models and interfaces
    models.py      CardIdentity, SourceCard, HistoricalPrice, etc.
    interfaces.py  CardSourceProvider abstract interface
  providers/
    myp/           MYP Cards provider implementation
      provider.py  HTTP client, discovery, price fetching
  parsers/
    myp.py         HTML + JSON-LD parsers for MYP Cards
  database/
    models.py      SQLAlchemy table definitions
    repository.py  CRUD operations with idempotency
  collectors/
    backfill.py    Orchestration: discover -> collect -> persist
  analytics/
    indicators.py  Pure analytics: MA, ATH/ATL, volatility, momentum
  api/
    app.py         FastAPI application factory
    deps.py        Dependency injection (get_db)
    jobs.py        In-memory job tracker
    routers/       Route handlers (cards, sets, market, collect)
    schemas/       Pydantic request/response models
  cli/
    main.py        Click CLI entry point

tests/
  fixtures/        Saved HTML responses for offline tests
  unit/
    test_analytics_models.py   Domain model tests (11)
    test_backfill.py           Concurrency/resume tests (11)
    test_cli_analytics.py      CLI analyze commands (8)
    test_indicators.py         Analytics functions (48)
    test_parsers.py            HTML/JSON-LD parsing (18)
    test_repository.py         DB upsert/batch tests (12)
    test_repository_queries.py Price series queries (10)
  integration/
    test_collector_pipeline.py Full pipeline tests (10)
```

## Data Model

```
cards                    Canonical card identity
  game, name_en, name_pt, set_code, collector_number

source_cards             Card as seen by a specific source
  source, external_id, sku, url, card_id

price_observations       Immutable weekly price snapshots
  source, external_id, observed_at (unique)
  median_price, tcg_price, last_sold_price, quantity_available

collection_errors        Failed collection attempts (for retry)
  source, external_id, url, error_type, error_message, resolved

exchange_rates           Daily USD/BRL exchange rates
  rate_date (unique), from_currency, to_currency, rate, source
```

## REST API

Start the API server:

```bash
# Via CLI
python -m src.cli.main serve

# Or directly with Uvicorn
python -m uvicorn src.api.app:create_app --factory --host 0.0.0.0 --port 8000
```

Auto-generated interactive docs are available at `/docs` (Swagger UI) and
`/redoc` (ReDoc) once the server is running.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/cards` | List cards (filter: `game`, `set`, `name`; cursor pagination) |
| GET | `/api/v1/cards/{id}` | Card detail with linked source cards |
| GET | `/api/v1/cards/{id}/history` | Price history (period: `30d`, `90d`, `180d`, `1y`, `3y`) |
| GET | `/api/v1/sets` | List sets with card counts |
| GET | `/api/v1/market/movers` | Top gainers and losers (period: `7d`, `30d`, `90d`) |
| GET | `/api/v1/market/stats` | Aggregate market statistics |
| POST | `/api/v1/collect/backfill` | Trigger backfill job (async, requires API key) |
| POST | `/api/v1/collect/update` | Trigger update job (async, requires API key) |
| GET | `/api/v1/collect/health` | Collection pipeline health (last run, stale cards, errors) |
| GET | `/api/v1/collection/{id}` | Collection entry detail (metadata, price history, external links) |
| POST | `/api/v1/collection/snapshot-prices` | Trigger daily JSON-LD price snapshot (async, requires API key) |
| POST | `/api/v1/scans` | Trigger a collection price scan with filters (async, requires API key) |
| GET | `/api/v1/scans` | List scan history with pagination |
| GET | `/api/v1/scans/{id}` | Scan detail with error summary |
| GET | `/api/v1/scans/{id}/stream` | SSE stream of scan progress events (auth via `?token=`) |
| POST | `/api/v1/schedules` | Create a scheduled scan (requires JWT) |
| GET | `/api/v1/schedules` | List user's scheduled scans |
| GET | `/api/v1/schedules/{id}` | Scheduled scan detail |
| PATCH | `/api/v1/schedules/{id}` | Update/pause/resume a schedule |
| DELETE | `/api/v1/schedules/{id}` | Delete a scheduled scan |
| POST | `/api/v1/schedules/{id}/trigger` | Trigger immediate scan run |
| GET | `/api/v1/exchange-rates/current` | Current USD/BRL exchange rate |
| GET | `/api/v1/exchange-rates/history` | Exchange rate history (query: `days`) |
| POST | `/api/v1/exchange-rates/refresh` | Fetch latest rate from BCB (requires API key) |

All responses use a standard envelope: `{"data": ..., "meta": {...}, "errors": []}`.
Every response includes a `X-Request-ID` header and `meta.request_id` for tracing.

**Authentication:** The collect endpoints (`backfill`, `update`) are protected by
an API key via the `X-API-Key` header. Set the `TCG_API_KEY` environment variable
to enable the guard. When `TCG_API_KEY` is unset, the guard is a no-op (dev mode).

## Data Source: MYP Cards

- Editions discovery via `/magic/edicoes?page={n}` (48 pages)
- Card listing per set via `/magic/{set-slug}`
- Card details via JSON-LD structured data on product pages
- Price history via `window.precoChartConfig` on `/magic/preco/{id}/{slug}?dias={n}`
- Supported periods: 30, 90, 180, 365, 1095 days
- Data resolution: weekly
- Uses `curl_cffi` with Chrome TLS fingerprint impersonation (Cloudflare)

## Running Tests

```bash
make test       # runs pytest with verbose output
make lint       # runs ruff check
make format     # runs ruff format
```

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System layers and data flow |
| [SETUP.md](docs/SETUP.md) | Installation and first run |
| [DEVELOPMENT.md](docs/DEVELOPMENT.md) | Coding conventions and workflow |
| [DATA_SOURCES.md](docs/DATA_SOURCES.md) | Data source details (MYP Cards) |
| [DATABASE.md](docs/DATABASE.md) | Schema and idempotency strategy |
| [API.md](docs/API.md) | Planned REST API surface |
| [ROADMAP.md](docs/ROADMAP.md) | Feature roadmap |
| [DECISIONS.md](docs/DECISIONS.md) | Architecture Decision Records index |
| [SECURITY.md](docs/SECURITY.md) | Security policies |
| [CONTRIBUTING.md](docs/CONTRIBUTING.md) | How to contribute |
| [AI_CONTEXT.md](docs/AI_CONTEXT.md) | Context for AI agents |

## Limitations

1. History resolution is weekly (not daily)
2. Maximum history depth is ~3 years (1095 days)
3. Cards with very few sellers may not have price history
4. Card names from JSON-LD are in Portuguese; EN names need search API enrichment
5. Cloudflare protection requires TLS fingerprint impersonation (`curl_cffi`)
6. No public API — data extracted from HTML + JSON-LD + inline JavaScript

## Shipped

### F01 — MYP Cards Backfill: Dominaria Remastered (2026-08-18)

Full backfill of the Dominaria Remastered (DMR) set was executed and validated:

- 30 cards collected, 0 failures
- 1889 price observations stored (date range: 2023-08-20 → 2026-08-16)
- Idempotency verified (re-run inserts 0 new observations)
- Incremental `update` command functional
- All 27 unit tests green

### F02 -- Project Reproducibility & Living Documentation (2026-08-18)

- Makefile with setup/test/lint/format/clean targets
- Bootstrap scripts for Mac and Linux
- Complete pyproject.toml with build-system metadata
- .env.example with all environment variables
- 11 living documentation files under docs/
- ADR-0002: Web stack decision (FastAPI, proposed)
- Architecture and journey diagrams for F02

### F03 -- Analytics Engine (2026-08-18)

Pure-function analytics engine for TCG price data with CLI integration:

- **Moving Averages** -- MA(7), MA(30), MA(90) simple moving averages
- **Price Extremes** -- All-Time High and All-Time Low with dates
- **Volatility** -- Standard deviation and coefficient of variation (30-day window)
- **Momentum** -- Rate of change (%) and trend direction (up/down/flat, 7-day window)
- CLI commands: `analyze list` (browse cards) and `analyze card <id>` (full report)
- All arithmetic uses `Decimal` for financial precision
- Zero side effects -- pure functions, no database imports in analytics module

Example usage:

```bash
# List available cards
python -m src.cli.main analyze list

# Analyze a specific card
python -m src.cli.main analyze card 12345

# Analyze using a different price field
python -m src.cli.main analyze card 12345 --price-field tcg_price
```

### F04 -- Collector Scaling (2026-08-18)

Prepared the collector pipeline to scale from 30 cards to the full MYP catalog:

- **Batch upsert** -- `INSERT ON CONFLICT DO NOTHING` replaces per-row SELECT+INSERT
- **Concurrent processing** -- `asyncio.Semaphore` with configurable concurrency (default 3)
- **Resume capability** -- skips cards already collected, resumable after interruption
- **Integration tests** -- 10 tests covering full pipeline (backfill, update, retry-failed)
- CLI flags: `--concurrency` and `--no-resume`
- 131 total tests (105 original + 26 new), 0 lint errors

### F06 -- REST API (2026-08-18)

FastAPI-based REST API exposing all collected data over HTTP:

- **8 endpoints** under `/api/v1`: cards (list, detail, history), sets, market (movers, stats), collect (backfill, update)
- Standard envelope format (`data`, `meta`, `errors`) on all responses
- Request ID middleware for tracing (`X-Request-ID` header)
- CORS middleware enabled, exception handlers for validation/HTTP/internal errors
- Cursor-based pagination on card listing
- Auto-generated OpenAPI docs at `/docs` and `/redoc`
- In-memory job tracker for async collection tasks
- Integration tests with seeded data covering all endpoints
- Architecture and journey diagrams

### F07 -- Front-end Dashboard (2026-08-18)

React SPA for visualizing TCG price data from the REST API:

- **4 pages**: Dashboard (KPIs + movers preview), Cards (search/filter/pagination),
  Card Detail (interactive price history chart), Market Movers (gainers/losers tables)
- **Tech stack**: Vite 6, React 19, TypeScript 5.8, Tailwind CSS, Recharts, React Router v7
- **Dark theme** by default, responsive layout (desktop + tablet)
- **Typed API client** with fetch wrapper, debounced search, cursor-based pagination
- **Component tests** with Vitest + React Testing Library
- Vite dev server proxies `/api` to FastAPI backend -- no CORS setup needed
- Architecture and user journey diagrams under `docs/diagrams/`

Running the front-end:

```bash
# Start the API server first (from project root)
python -m src.cli.main serve

# Then start the front-end (in a separate terminal)
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

### F08 -- Data Enrichment (2026-08-19)

Fixed data quality issues discovered during manual testing of the F07 dashboard:

- **UTF-8 encoding fix** -- resolved double-encoding of Portuguese card names
  (e.g., "ContramaÃÂ§ica" now correctly displays "Contramagica") in both the
  parser/provider pipeline and existing DB data via migration script
- **Movers default period** -- changed Dashboard movers from 7d to 30d so that
  price changes are non-zero with weekly-resolution data
- **Collection expansion** -- backfill script for multiple popular Magic sets
  beyond the initial Dominaria Remastered dataset
- **15 new encoding tests** added; total backend tests now 405, frontend 165

### F09 -- Scheduled Collection & Observability (2026-08-19)

Automated daily price collection with pipeline observability and API security:

- **Health endpoint** -- `GET /api/v1/collect/health` returns last collection
  timestamp, stale cards count, recent error count, and overall status
  (`healthy`, `stale`, or `error`)
- **API key protection** -- POST collect endpoints (`backfill`, `update`) now
  require an `X-API-Key` header when `TCG_API_KEY` env var is set; no-op guard
  in dev mode when unset
- **Cron trigger script** -- `scripts/cron_update.sh` calls the update endpoint
  with the API key, logs results to `logs/cron/`, and exits with meaningful
  status codes for cron/scheduler integration
- **Dashboard freshness indicator** -- Dashboard page shows "Last updated: X ago"
  derived from the health endpoint, with graceful degradation if unreachable
- Scheduling docs for Linux/Mac (crontab) and Windows (Task Scheduler)
- Architecture and journey diagrams under `docs/diagrams/`

### F10 -- Collection-Centric Pivot (2026-08-19)

Pivoted the platform from a generic market scanner to a personal collection
tracker. The user's imported collection is now the source of truth -- the
database tracks only cards the user owns, and the dashboard shows
collection-specific intelligence (portfolio value, coverage, per-card images).

- **Collection import** -- CSV import into `user_collection` table with
  set code, collector number, quantity, quality, language, and rarity
- **Match report** -- `match-report` CLI command runs a dry-run search
  against MYP Cards and reports matched/ambiguous/unmatched coverage
  before any destructive operations
- **DB maintenance** -- `db-backup` creates timestamped SQLite backups;
  `db-cleanup` removes cards, source_cards, and price_observations not
  linked to the user's collection (with automatic backup)
- **Sync pipeline** -- `sync-collection` CLI command orchestrates search,
  match, card detail fetch, price history fetch, and DB upsert for each
  collection card; also available as `POST /api/v1/collection/sync`
- **Collection API** -- `GET /api/v1/collection` lists collection cards
  with latest prices and Scryfall image URLs; `GET /api/v1/collection/summary`
  returns portfolio KPIs
- **Dashboard collection KPIs** -- shows unique cards, total copies,
  estimated portfolio value, and coverage percentage
- **Scryfall HD images** -- Card Detail and My Collection pages display
  card artwork via Scryfall's redirect API
- **Set code normalization** -- all set codes normalized to lowercase
  across import, matching, and storage
- Architecture decision: [ADR-0004](docs/adr/0004-collection-centric-pivot.md)

### F11 -- Post-F10 Operationalization (2026-08-20)

Operationalized the production database after F10 and cleaned up tech debt:

- **Parser fix** -- `parse_search_results()` field names updated to match
  MYP's current API (`idproduto`/`nomeenproduto`/`slugnomeenproduto`),
  with backward-compatible fallback chain
- **Match report** -- 94.7% match rate (519/548 collection cards found on MYP)
- **Collection sync** -- 124 cards linked to collection entries; however,
  MYP price history pages no longer serve data (0 new observations --
  blocker for future price collection features)
- **Tech debt** -- extracted shared `_row_to_entry` converter, moved raw
  SQLAlchemy from router to `Repository.get_collection_total_value()`,
  removed dead `BASE_URL` constant
- **Tests:** 616 backend + 187 frontend, 91.44% coverage

### F12 -- JSON-LD Price Snapshot (2026-08-20)

Daily price collection from public JSON-LD product data, replacing the
auth-walled price history endpoint that MYP Cards locked down on 2026-08-20:

- **Parser** -- `parse_jsonld_price()` extracts `price`, `currency`, and
  `availability` from the `@type: Product` / `offers.price` JSON-LD block
  on MYP product pages (public, no auth required)
- **Provider** -- `fetch_current_price()` fetches a product page and returns
  a `JsonLdPrice` dataclass
- **Snapshot collector** -- `src/collectors/snapshot_prices.py` iterates
  linked collection entries, checks idempotency (skip if card+date already
  has a snapshot), and stores observations with `source="jsonld_snapshot"`
- **CLI** -- `python -m src.cli.main snapshot-prices` with `--limit`,
  `--dry-run`, `--delay`, `--concurrency` options
- **API** -- `POST /api/v1/collection/snapshot-prices` endpoint with API key
  auth, runs as background job
- **Cron** -- `scripts/cron_update.sh` now calls snapshot-prices after the
  existing daily update
- **Frontend** -- PriceChart handles sparse data (fewer than 2 points)
  gracefully with an empty-state message

Price history builds organically: after 7 daily runs, charts show trends;
after 30 days, analytics (MA, ATH/ATL, volatility) have sufficient data.

### F13 -- Collection Scans (2026-08-20)

Unified scan orchestrator with filter support (by collection, set, format,
rarity, or custom card list). Each scan run is persisted with full metrics
(cards total/processed/failed, observations saved) for auditing and
historical analysis.

- **Scan orchestrator** -- `src/collectors/scan.py` replaces ad-hoc
  snapshot/sync commands with a structured, trackable scan model
- **Filters** -- scans can target a specific set code, format, rarity,
  or an explicit list of card IDs
- **Persistent tracking** -- new `scan_runs` table stores every execution
  with status, timestamps, filter JSON, and card count metrics
- **CLI** -- `scan` (trigger with filters) + `scan-history` (view past runs)
- **API** -- `POST /api/v1/scans` (trigger), `GET /api/v1/scans` (list),
  `GET /api/v1/scans/{id}` (detail with error summary)
- **Frontend** -- Price Scans page with trigger form and history table

### F15 -- Collection Display Fixes (2026-08-20)

Three display fixes for the collection experience:

- **Variant card images** -- MYP uses non-standard set codes for variant
  printings (borderless, extended art, showcase, Secret Lair). A mapping
  utility (`set_code_map`) translates these to Scryfall-compatible codes
  so card images load correctly. Three-tier resolution: static lookup
  table, Secret Lair regex, prefix-stripping heuristic.
- **BRL currency indicator** -- Sidebar now shows the Brazilian flag and
  "BRL" label so users always know the active currency.
- **Collection card detail view** -- New `/collection/:id` route with
  dedicated detail page. Shows collection metadata (quantity, quality,
  language, extras), card image, latest price, price chart (if linked),
  source links, and external links (Scryfall, LigaMagic). Eliminates
  dead-end navigation for unlinked cards.

### F16 -- Explore Cards Sorting (2026-08-21)

Added sorting controls to the My Collection page so users can reorder
their cards by different criteria:

- **Sort fields**: Name (A-Z / Z-A), Set, Card Number, Date Added
  (Newest / Oldest), Price (High-Low / Low-High)
- **Backend sorting** for name, set, number, and date added via
  `sort_by` and `sort_dir` query parameters on `GET /api/v1/collection`
- **Client-side sorting** for price (avoids JOIN overhead; null prices
  pushed to end)
- **Offset pagination** replaces cursor-based pagination for stable
  sort ordering (backward-compatible: cursor param still works)
- **URL-persisted sort state** via query parameters (`?sort=...&dir=...`)
- **SortSelect component** -- reusable dropdown with configurable options

### F17 -- Set Symbol Icons (2026-08-21)

Replaced text-based set filter chips on the My Collection page with
Scryfall set symbol SVG icons:

- **Set icon utility** -- `scryfallSetIconUrl()` builds Scryfall SVG URLs
  with MYP variant set code mapping (reuses existing `mapToScryfallSetCode`)
- **SetIconFilter component** -- compact icon buttons with tooltips (full
  set name on hover), highlight ring on selection, text fallback on SVG
  load error
- **Simplified labels** -- set filter options now show just the set name
  (icon conveys the code visually)

### F20 -- Card Grid Size Control (2026-08-21)

Added a 3-option grid size toggle (Small / Medium / Large) to the
collection page, persisted in localStorage:

- **useGridSize hook** -- reads/writes grid size preference to
  `localStorage` with `"md"` default and invalid-value fallback
- **GridSizeToggle component** -- accessible button group with SVG grid
  density icons, `aria-pressed` states, and cyan highlight on active
- **Dynamic grid layout** -- both skeleton and card grids use Tailwind
  classes from `GRID_SIZE_CONFIG`; Small mode shows compact cards
  (name + price only), Large mode shows full card info
- **Persistent preference** -- grid size survives page reload

### F22 -- Authentication (Login Area) (2026-08-21)

Added user authentication with email+password and JWT-based sessions.
Collection and scan endpoints are now protected by user auth:

- **User model** -- new `users` table with email, display name, avatar URL,
  auth provider (email/google/microsoft/apple), provider ID, password hash,
  and active flag. BCrypt password hashing via `bcrypt` library.
- **JWT tokens** -- HS256 access tokens (30 min) and refresh tokens (7 days)
  via `python-jose`. Secret via `TCG_JWT_SECRET` env var (auto-generated in dev).
- **Auth API** -- `POST /api/v1/auth/register`, `/login`, `/refresh`, `/logout`,
  `GET /api/v1/auth/me`. OAuth endpoints (`/{provider}`, `/{provider}/callback`)
  return 501 until provider credentials are configured.
- **Dual auth** -- protected endpoints accept EITHER JWT (browser users) OR
  X-API-Key (cron/CLI). In dev mode (no `TCG_API_KEY` set), unauthenticated
  access falls through for backward compatibility.
- **Frontend auth** -- `AuthProvider` context, `useAuth()` hook, Login page
  with email/password form and mode toggle (sign in / create account),
  `ProtectedRoute` component guarding `/collection` and `/scans` routes.
- **Layout updates** -- sidebar shows real user name + sign-out button when
  authenticated, or sign-in link when not. Nav items conditionally visible.
- **Collection migration** -- `migrate-user` CLI command moves collection
  entries from old user ID to new user ID.
- **OAuth placeholder** -- Google, Microsoft, Apple OAuth buttons present
  but disabled (configuration-only; full flow requires setting env vars).

### F18 -- Multi-Currency Support (BRL + USD) (2026-08-21)

Added support for viewing all prices in either BRL or USD, with real-time
currency conversion using BCB PTAX exchange rates:

- **Exchange rate storage** -- new `exchange_rates` table with daily
  USD/BRL rates. ExchangeRateRow model with unique date constraint and
  upsert support.
- **BCB PTAX client** -- async client (`src/providers/bcb/client.py`)
  fetches daily rates and date ranges from the Brazilian Central Bank
  API. Returns `ExchangeRate` domain objects.
- **CurrencyConverter service** -- read-time conversion with per-request
  cache. Divides BRL prices by the exchange rate for the observation
  date. Falls back to closest previous business day when exact date has
  no rate. Returns null when no rate data exists.
- **CLI** -- `update-exchange-rate` command with `--date` and
  `--backfill-days` options. Backfill script at
  `scripts/backfill_exchange_rates.py` for initial 365-day population.
- **API** -- `?currency=BRL|USD` query parameter on all price endpoints
  (cards, collection, market movers, stats). New exchange rate endpoints:
  `GET /api/v1/exchange-rates/current` and
  `GET /api/v1/exchange-rates/history`.
- **Frontend** -- BRL/USD toggle in sidebar (replaces static BRL indicator),
  persistent via localStorage with cross-tab sync. All price displays
  use `formatCurrency()` with locale-aware formatting (R$ for BRL,
  $ for USD).
- **Architecture decision:** [ADR-0005](docs/adr/0005-multi-currency-read-time-conversion.md)
  documents the read-time conversion approach.

### F19 -- Moeda Pila (Regional Currency) (2026-08-21)

Added "Pila" as a third currency option -- a regional currency used in
Rio Grande do Sul (Brazil), 1:1 with BRL, displayed in extenso format
(e.g., "230 pilas e 21 centavos"):

- **Pila formatter** -- `src/currency/pila_formatter.py` with `format_pila()`
  function using pt-BR thousands separator, singular/plural inflection for
  "pila"/"pilas" and "centavo"/"centavos", centavos omitted when zero.
  Mirrored as `formatPila()` in `frontend/src/utils/format.ts`.
- **Currency enum** -- `PILA` added to `Currency` enum in domain models.
  `CurrencyConverter.convert()` treats PILA as 1:1 with BRL (no exchange
  rate lookup). All API router `?currency=` validators updated to accept
  `BRL|USD|PILA`.
- **Frontend formatter** -- `formatCurrency()` dispatcher routes `PILA` to
  `formatPila()`. `CurrencyCode` type extended to include `"PILA"`.
- **RS flag** -- simplified Rio Grande do Sul state flag SVG at
  `frontend/src/assets/rs-flag.svg`. `CurrencyIndicator` component renders
  the flag for PILA, "R$" for BRL, "$" for USD. Integrated into Dashboard,
  MyCollection, and CollectionCardDetail price displays.
- **CurrencyToggle** -- 3-button toggle (BRL / USD / Pila) with RS flag
  icon on the Pila button. `toggle()` cycles through all three currencies.
- **User preference** -- `preferred_currency` field on `UserRow` and `User`
  models (default "BRL"). `PATCH /api/v1/auth/me/preferences` endpoint
  accepts `{"preferred_currency": "BRL"|"USD"|"PILA"}`. Profile endpoint
  includes `preferred_currency` in response.

### F23 -- Deck Import (2026-08-21)

Added deck management: import deck lists from text or CSV, view deck
contents with visual ownership indicators, and navigate to card detail pages.

- **Database models** -- new `decks` and `deck_cards` tables with indexes
  for user and card lookups
- **Deck parser** -- text format parser supporting `{qty} {name}`,
  `{qty} {name} [{set}]`, `{qty} {name} [{set}:{number}]` with comments
  and blank line handling. CSV parser reuses collection column mapping.
- **Deck importer** -- orchestrates parsing, card linking (set+number
  exact match, then unique name match), and storage
- **Repository methods** -- 9 new methods: create_deck, add_deck_cards,
  get_deck, list_decks, delete_deck, get_deck_cards,
  get_deck_cards_with_ownership (3-tier matching: card_id, set+number,
  name), get_deck_summary, link_deck_card
- **API endpoints** -- `POST /api/v1/decks` (import from text/CSV),
  `GET /api/v1/decks` (list with summaries), `GET /api/v1/decks/{id}`
  (detail with ownership + images + prices), `DELETE /api/v1/decks/{id}`
- **Frontend** -- DeckList page (grid of deck cards with ownership %),
  DeckView page (card grid with darkened overlay for unowned cards),
  DeckImportModal (name, format toggle, content textarea, description),
  DeckCardTile (ownership overlay, quantity badge, navigation to
  collection or card detail)
- **API client** -- `apiPost` and `apiDelete` helpers added to client.ts
  for non-GET requests with auth token support
- **Navigation** -- "My Decks" nav item in sidebar (auth required),
  `/decks` and `/decks/:id` protected routes

### F24 -- Platform Polish & Fixes (2026-08-21)

Batch of bug fixes, UX improvements, and cross-cutting enhancements:

- **Collection card detail fix** -- `apiGet` now sends JWT auth headers
  (matching `apiPost`/`apiDelete`), and the collection detail endpoint
  checks entry ownership (IDOR prevention). Clicking a card in My
  Collection now correctly opens its detail page.
- **Explore Cards images** -- image fallback chain uses `name_en` for
  Scryfall lookups. Cards with Portuguese-only names show clean placeholders.
- **Explore Cards prices** -- `formatPriceOrFallback()` helper shows
  "No price data" (muted text) instead of misleading "R$ 0,00" for
  unpriced cards.
- **Dashboard coverage breakdown** -- new `priced_count` metric shows
  both "linked" and "priced" percentages with explanatory text. Low
  coverage hint suggests syncing with MYP.
- **Interactive price chart** -- Recharts Brush for time range selection,
  click-drag zoom via ReferenceArea, dynamic Y-axis (no more R$100 cap),
  crosshair cursor, and reset zoom button.
- **i18n (EN + PT-BR)** -- react-i18next setup with full string extraction
  across all pages and components. LanguageContext with localStorage
  persistence. LanguageSelector on login page and sidebar.
- **Language preference** -- `preferred_language` column on users table,
  synced via `PATCH /auth/me/preferences`. Language choice persists
  across sessions.
- **Visual redesign** -- dark theme with `tcg-*` design tokens (CSS custom
  properties + Tailwind extend). Glass-morphism cards, vibrant accent
  colors, consistent typography hierarchy, hover effects across all
  components.
- **New API helper** -- `apiPatch()` added to frontend API client.
- **Tests:** 1179 backend (94.87% coverage), 479 frontend (48 files)

### F32 -- Real-time Scan Progress (SSE) (2026-08-21)

Replaced 3-second polling with Server-Sent Events (SSE) for real-time scan
progress streaming. Each card scanned produces an event with its name,
price result, and running totals. The collection grid updates as data
arrives instead of waiting for a full re-fetch at the end.

- **Event bus** -- in-memory pub/sub using `asyncio.Queue` per scan,
  keyed by scan_id. Thread-safe publishing via `call_soon_threadsafe`
  for the background scan thread.
- **ScanEvent model** -- `src/domain/events.py` dataclass with
  `to_sse_json()` serialization (scan_started, card_scanned, scan_complete).
- **SSE endpoint** -- `GET /api/v1/scans/{id}/stream?token=<jwt>` returns
  `text/event-stream`. Auth via query param (EventSource limitation).
  Keepalive comments every 30s. Returns final event for already-completed scans.
- **useScanStream hook** -- wraps EventSource with typed event parsing,
  progress state, and automatic fallback to 3s polling on SSE failure.
- **useCollectionRefresh v2** -- swapped setInterval polling for SSE via
  useScanStream. Public API unchanged (isRefreshing, progress, startRefresh,
  cancelRefresh). New `lastScannedCard` field for per-card details.
- **ScanProgressBar component** -- enhanced progress display with current
  card name, price-found ratio, and estimated time remaining.
- **Live card updates** -- card prices update in the collection grid as
  scan events arrive, with 2-second highlight animation (green for price
  found, amber for no price).
- **Backwards compatible** -- existing polling endpoint still works.
- **i18n** -- 9 new keys in EN and PT-BR for streaming progress UI.

### F37 -- Scheduled Scans (2026-08-21)

Added automated scheduling for collection price scans using APScheduler,
so users can set up recurring scan jobs (e.g., daily at 6am) without
manual intervention:

- **APScheduler 3.x integration** -- `ScanScheduler` service wraps a
  `BackgroundScheduler` with `CronTrigger` jobs. Starts/stops via
  FastAPI lifespan context manager. Controlled by `TCG_SCHEDULER_DISABLED`
  env var for test/CI environments.
- **Domain model** -- `ScheduledScan` dataclass and `ScheduleStatus` enum
  (`active`, `paused`, `disabled`). `ScheduledScanRow` SQLAlchemy model
  with user_id, cron expression, scan type, filters, error tracking.
- **Repository CRUD** -- 8 new methods: create, get, list (with user
  filter + pagination), count, update, delete, get_active_schedules.
  Per-user limit of 10 active schedules enforced at API level.
- **Cron validation** -- `validate_cron()` rejects sub-hour intervals
  (bare `*` or `*/N` where N<60 in minute field). Uses `croniter` for
  expression parsing and next-run calculation.
- **Auto-pause on failure** -- consecutive errors tracked via
  `error_count`. When `error_count >= max_retries`, schedule is
  automatically paused. Successful runs reset the counter.
- **Concurrency guard** -- `threading.Lock` prevents overlapping
  executions of the same schedule.
- **API endpoints** -- 6 endpoints under `/api/v1/schedules`: POST
  (create), GET list, GET detail, PATCH (update/pause/resume), DELETE,
  POST trigger (run now). All require JWT auth.
- **CLI commands** -- `schedule-list` (table display with status filter),
  `schedule-add` (with cron validation), `schedule-remove` (by ID).
- **Frontend** -- Schedules page with full CRUD: ScheduleForm (cron
  presets for Daily 6am, Every 12h, Weekly Monday, Monthly),
  ScheduleTable (status badges, error count, action buttons for
  pause/resume/trigger/edit/delete), loading/error/empty states.
- **i18n** -- 30+ keys in EN and PT-BR for schedule management UI.
- **Tests:** 71 new backend tests, 20 new frontend tests (91 total).

## Future

Prepared for but not yet implemented:

- Advanced analytics (correlation, portfolio-level aggregation, alerts)
- Portfolio tracking (cost basis, P&L, ROI)
- Opportunity scoring
- Additional sources (Liga Magic, Scryfall metadata, CardMarket, TCGPlayer)
- Frontend dashboard
