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
| POST | `/api/v1/collect/backfill` | Trigger backfill job (async) |
| POST | `/api/v1/collect/update` | Trigger update job (async) |

All responses use a standard envelope: `{"data": ..., "meta": {...}, "errors": []}`.
Every response includes a `X-Request-ID` header and `meta.request_id` for tracing.

**Note:** Authentication is not yet implemented. The API is intended for local
or trusted-network use only in this phase.

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

## Future

Prepared for but not yet implemented:

- Advanced analytics (correlation, portfolio-level aggregation, alerts)
- Portfolio tracking (cost basis, P&L, ROI)
- Opportunity scoring
- Additional sources (Liga Magic, Scryfall metadata, CardMarket, TCGPlayer)
- Frontend dashboard
