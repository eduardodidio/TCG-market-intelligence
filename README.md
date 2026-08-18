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

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--db` | `sqlite:///tcg_market.db` | Database connection string |
| `--set` | all sets | Only collect from this set slug |
| `--limit` | unlimited | Max cards to process |
| `--dry-run` | off | Don't write to database |
| `--delay` | 1.0 | Seconds between requests |
| `--history-days` | 1095 | Days of price history to fetch |

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
  cli/
    main.py        Click CLI entry point

tests/
  fixtures/        Saved HTML responses for offline tests
  unit/
    test_parsers.py     Parser tests (27 tests)
    test_repository.py  Database tests
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

## Future

Prepared for but not yet implemented:

- Market analytics (moving averages, ATH/ATL, volatility, momentum)
- Portfolio tracking (cost basis, P&L, ROI)
- Opportunity scoring
- Additional sources (Liga Magic, Scryfall metadata, CardMarket, TCGPlayer)
- REST API (`GET /cards`, `/cards/{id}/history`, `/market/movers`)
- Frontend dashboard
