# F03 — Analytics Engine

**Status:** planned
**Created:** 2026-08-18

## Goal

Compute market analytics indicators (moving averages, ATH/ATL, volatility,
momentum) from collected price observations stored in SQLite.  Analytics
are pure computations over time-series data -- no new data collection,
no external API calls.

## Architecture Impact

- **New module** `src/analytics/` -- pure-function engine, no side effects.
- **Existing** `src/database/repository.py` -- add query methods to fetch
  price time-series for a card.
- **Existing** `src/domain/models.py` -- add dataclasses for analytics results.
- **Existing** `src/cli/main.py` -- add `analyze` subcommand group.

## Global Acceptance Criteria

1. **AC1** All analytics functions have unit tests with >= 90% branch coverage
2. **AC2** CLI `analyze` command prints indicators for a given card
3. **AC3** Pure functions -- no database access inside analytics module
4. **AC4** All existing 27 tests still pass
5. **AC5** Architecture and journey diagrams created
6. **AC6** README.md updated with new capability

## Waves

- **Wave 0**: F03-T01, F03-T02  (domain models + scaffolding, repository queries)
- **Wave 1**: F03-T03            (all analytics indicators)
- **Wave 2**: F03-T04, F03-T05  (CLI integration, diagrams + README)

## Diagrams

- `docs/diagrams/F03-architecture.mmd`
- `docs/diagrams/F03-journey.mmd`
