# PRD: F18 — Multi-Currency Support (BRL + USD)

## Problem Statement

All prices in TCG Market Intelligence are stored and displayed in BRL
(Brazilian Real), sourced from MYP Cards. Users who want to compare prices
with international markets (TCG Player, Card Kingdom, etc.) have no way to
see values in USD. Manual conversion is error-prone because the BRL/USD
exchange rate fluctuates daily.

## Goal

Add a transparent BRL/USD conversion layer that:

1. Fetches the daily PTAX exchange rate from the BCB (Banco Central do
   Brasil) public API once per day.
2. Stores a historical exchange rate table so that past price observations
   can be converted at the rate that was valid on the observation date.
3. Exposes a `currency` query parameter on API endpoints that return
   prices, defaulting to BRL (no breaking change).
4. Provides a frontend currency toggle that persists across sessions.
5. Does NOT change how prices are stored — BRL remains the canonical
   storage currency. Conversion is always performed at read time.

## Non-Goals

- Supporting currencies other than BRL and USD.
- Changing the storage currency of price observations.
- Integrating with paid exchange rate APIs.
- Real-time (sub-daily) exchange rate updates.

## Data Source

BCB PTAX API (free, public, no authentication):

```
GET https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/
    CotacaoDolarDia(dataCotacao=@d)?
    @d='08-21-2026'&
    $format=json
```

Response contains `cotacaoCompra` (buy) and `cotacaoVenda` (sell).
We use `cotacaoVenda` (sell rate) for conversion, which is the standard
market convention for pricing imports.

Fallback: if the BCB API is unavailable or returns no data for a
given date (weekends/holidays), use the most recent available rate.

## Architecture Decisions

### AD-1: Read-time conversion, not write-time duplication

Prices remain stored in BRL. When the API receives `?currency=USD`, it
converts using the exchange rate for the observation date. This avoids
data duplication and keeps the single-source-of-truth principle.

### AD-2: New `exchange_rates` table

```
exchange_rates
  id            INTEGER PK
  rate_date     DATE NOT NULL UNIQUE
  from_currency VARCHAR(3) NOT NULL DEFAULT 'USD'
  to_currency   VARCHAR(3) NOT NULL DEFAULT 'BRL'
  rate          NUMERIC(12,6) NOT NULL
  source        VARCHAR(50) DEFAULT 'bcb_ptax'
  created_at    DATETIME
```

The rate stored is "1 USD = X BRL" (e.g., 5.45). To convert BRL to USD,
divide by the rate. This matches the PTAX `cotacaoVenda` semantics.

### AD-3: Frontend currency state via localStorage

The selected currency (`BRL` or `USD`) is stored in `localStorage` and
passed as a query parameter to all price-returning API calls. No server
session needed.

### AD-4: Graceful degradation

If no exchange rate exists for a requested date, the system falls back
to the closest previous rate. If no rates exist at all, USD conversion
returns null values with a warning, and BRL values are shown.

## User Stories

1. **As a user**, I want to toggle between BRL and USD on any page that
   shows prices, so I can compare values with international markets.
2. **As a user**, I want the currency preference to persist across
   browser sessions.
3. **As an operator**, I want a CLI command to fetch and store today's
   exchange rate, so I can run it via cron.
4. **As a developer**, I want an API endpoint to check the current
   exchange rate and its freshness.

## API Changes

### New Endpoints

- `GET /exchange-rates/current` — returns the latest exchange rate
- `GET /exchange-rates/history?days=30` — returns rate history
- `POST /exchange-rates/refresh` (auth required) — triggers a rate fetch

### Modified Endpoints (add `?currency=BRL|USD` parameter)

- `GET /cards` — `latest_price` converted
- `GET /cards/{id}` — `latest_price` converted
- `GET /cards/{id}/history` — all price fields converted
- `GET /collection` — `latest_price` converted
- `GET /collection/summary` — `total_value` converted
- `GET /collection/{id}` — `latest_price` and `price_history` converted
- `GET /market/stats` — `avg_price` converted
- `GET /market/movers` — `price_start`, `price_end` converted

All responses gain a `currency` field in the response (already present
on PriceObservation, needs adding to card summaries and collection
summaries).

## Frontend Changes

- Currency toggle component (BRL / USD) in the Layout header.
- `formatCurrency(value, currency)` replaces hardcoded `formatBRL()`.
- All API calls pass `?currency=<selected>`.
- Price chart Y-axis label changes based on currency.

## Success Criteria

- [ ] Exchange rate table populated with at least 30 days of historical data
- [ ] CLI `update-exchange-rate` command works and is idempotent
- [ ] All price-returning API endpoints accept `?currency=USD` and return
      correctly converted values
- [ ] Frontend toggle switches all displayed prices without page reload
- [ ] Currency preference persists across browser sessions
- [ ] Fallback works when rate is missing for a specific date
- [ ] No existing tests break (BRL remains default behavior)
- [ ] Backend tests >= 70% coverage maintained
- [ ] Frontend tests cover currency toggle and formatting
