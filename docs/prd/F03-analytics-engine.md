# PRD: F03 - Analytics Engine

**Status:** Delivered
**Date:** 2026-08-18
**Author:** Eduardo Rutkoski Didio

## Problem

The collector (F01) stores raw price observations -- median, TCG, last-sold,
and volume -- but provides no derived indicators. Users cannot answer
questions like "is this card trending up?", "what was its all-time high?",
or "how volatile is this card's price?" without manually analyzing the
raw time-series data. The project needs a computation layer that transforms
raw observations into actionable market indicators.

## Goals

1. Compute Moving Averages (MA) over 7, 30, and 90-day windows
2. Detect All-Time High (ATH) and All-Time Low (ATL) with dates
3. Calculate price volatility (standard deviation over configurable windows)
4. Compute momentum (percentage price change over configurable periods)
5. Implement all analytics as pure functions with no side effects
6. Add repository query methods to fetch price time-series for a card
7. Add domain dataclasses for analytics results
8. Provide a CLI `analyze` subcommand group for card-level and list-level analysis

## Non-Goals (this phase)

- Machine learning predictions or forecasting
- Real-time price alerts or notifications
- Persisting computed analytics to the database
- External API exposure of analytics results
- Portfolio-level aggregations

## Technical Analysis

### Architecture

The analytics engine follows a pure-function architecture:

- **`src/analytics/indicators.py`** -- all indicator functions are pure:
  they accept `list[PriceObservation]` and return analytics dataclasses.
  No database access, no I/O, no side effects.
- **`src/domain/models.py`** -- new dataclasses (`MovingAverage`,
  `HighLow`, `Volatility`, `Momentum`, `CardAnalytics`) hold results.
- **`src/database/repository.py`** -- new query methods fetch time-series
  data and pass it to the analytics layer.
- **`src/cli/main.py`** -- `analyze card` and `analyze list` subcommands
  wire repository queries to analytics functions and format output.

### Design Decisions

- All computations use `Decimal` arithmetic to avoid floating-point
  precision issues with financial data.
- Analytics functions are stateless and testable in isolation -- the
  database layer is only responsible for fetching input data.

## Acceptance Criteria

1. **AC1:** All analytics functions have unit tests with >= 90% branch coverage
2. **AC2:** CLI `analyze` command prints indicators for a given card
3. **AC3:** Pure functions -- no database access inside analytics module
4. **AC4:** All existing tests still pass (27 at time of delivery)
5. **AC5:** `F03-architecture.mmd` and `F03-journey.mmd` diagrams created
6. **AC6:** README.md updated with new analytics capability
