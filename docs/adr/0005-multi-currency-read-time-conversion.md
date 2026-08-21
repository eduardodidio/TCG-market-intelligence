# ADR-0005: Multi-Currency Read-Time Conversion

**Date:** 2026-08-21
**Status:** Accepted
**Feature:** F18 Multi-Currency Support

## Context

TCG Market Intelligence stores all prices in BRL (Brazilian Real), scraped
from MYP Cards. Users requested the ability to view prices in USD as well.

We needed to decide how to implement currency conversion:

1. **Write-time conversion** -- store both BRL and USD prices for every
   observation. Requires re-processing all historical data when exchange
   rates change.

2. **Read-time conversion** -- store prices in BRL only, convert at API
   response time using the exchange rate for the observation date.

3. **Dual storage with materialized views** -- maintain a separate table
   of USD-converted prices, refreshed periodically.

## Decision

We chose **read-time conversion** (option 2).

All prices remain stored in BRL. When a user requests `?currency=USD`,
the API layer divides each BRL price by the USD/BRL exchange rate for
the observation date (or the closest previous business day if no rate
exists for that exact date).

Exchange rates are fetched daily from the BCB (Brazilian Central Bank)
PTAX API and stored in the `exchange_rates` table. A CLI command
(`update-exchange-rate`) and a one-time backfill script handle rate
population.

The `CurrencyConverter` service handles conversion with an in-memory
cache per request to avoid repeated database lookups for the same date.

## Consequences

### Positive

- **No data duplication.** Prices are stored once in their source
  currency (BRL). The exchange_rates table is small (one row per
  business day).

- **Retroactive accuracy.** If a more accurate exchange rate is
  inserted for a historical date, all historical price queries
  automatically reflect the correction.

- **Simple schema.** No schema migration needed for existing price
  observation tables. Only the new `exchange_rates` table was added.

- **Extensible.** Adding more currencies (EUR, etc.) requires only
  adding exchange rate data, not changing the storage format.

### Negative

- **Slight latency overhead.** Each USD request requires an extra
  database lookup for the exchange rate. Mitigated by the per-request
  cache in CurrencyConverter.

- **Null prices when rates are missing.** If the exchange_rates table
  is empty or has no rate for a given date range, USD prices return as
  null rather than showing potentially stale conversions.

- **Rate dependency.** The system depends on daily BCB PTAX API
  availability. BCB may not publish rates on weekends/holidays, so the
  closest previous business day's rate is used as fallback.

## Alternatives Considered

**Write-time conversion** was rejected because it would require
reprocessing all ~5000+ price observations whenever a rate correction
is needed, and it doubles the storage footprint for price data.

**Materialized views** were rejected as over-engineering for the
current scale (SQLite, single-user). This approach could be revisited
if the system scales to PostgreSQL with many concurrent users.
