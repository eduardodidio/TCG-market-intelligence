# Roadmap

## Vision

TCG Market Intelligence aims to be a comprehensive market intelligence
platform for trading card games. Starting with Magic: The Gathering on the
Brazilian market, the project will grow to cover multiple sources, provide
analytics, and offer actionable buy/sell signals.

## Phase 1: Data Collection -- DONE

**Feature:** F01 -- MYP Cards Backfill

Delivered a working data collection pipeline:

- Card discovery across all MYP Cards editions (~48 pages)
- Current price extraction (min, average, TCG Player reference)
- Historical price collection (up to 3 years, weekly resolution)
- SQLite storage with full idempotency (no duplicate observations)
- Graceful error handling with retry support
- CLI commands: `backfill`, `update`, `retry-failed`
- 27 unit tests passing
- Validated with Dominaria Remastered: 30 cards, 1889 observations

## Phase 2: Project Quality -- IN PROGRESS

**Feature:** F02 -- Reproducibility and Documentation

Improving project reproducibility and documentation:

- `pyproject.toml` with pinned dependencies and dev extras
- `CONTRIBUTING.md` with setup and workflow instructions
- `docs/SETUP.md` with step-by-step environment setup
- Living documentation: API.md, ROADMAP.md, DECISIONS.md
- Architecture and user-journey diagrams (Mermaid)
- ADR for web stack decision (FastAPI)

## Phase 3: Analytics Engine

Market analytics computed from collected price data:

- Moving averages (7d, 30d, 90d)
- All-time high / all-time low detection
- Volatility metrics
- Momentum indicators (rate of change, trend direction)

## Phase 4: REST API

Expose data and analytics through a FastAPI REST API:

- Card listing and search with filters
- Price history endpoints with period selection
- Market movers (top gainers/losers)
- Aggregate market statistics
- Admin endpoints for triggering collection jobs
- See [API.md](API.md) for the full planned endpoint reference

## Phase 5: Portfolio Tracking

Personal portfolio management features:

- Track owned cards with purchase price and date
- Cost basis calculation
- Profit & loss (P&L) tracking
- Return on investment (ROI) calculations

## Phase 6: Frontend Dashboard

Web-based visualization:

- Price charts with configurable time ranges
- Portfolio overview and performance graphs
- Market movers and trending cards
- Set-level statistics and comparisons

## Phase 7: Multi-Source

Expand data collection beyond MYP Cards:

- Liga Magic (Brazilian market, alternative pricing)
- Scryfall (card metadata, images, Oracle text)
- CardMarket (European market)
- TCGPlayer (North American market)

## Phase 8: Opportunity Scoring

ML-based buy/sell signal generation:

- Price anomaly detection
- Cross-source arbitrage identification
- Trend prediction models
- Configurable alert thresholds

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions and
development workflow.
