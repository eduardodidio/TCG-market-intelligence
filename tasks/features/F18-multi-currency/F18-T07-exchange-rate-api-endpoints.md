# F18-T07: Exchange Rate API Endpoints

- **Wave:** 2
- **Status:** done
- **Depends on:** F18-T04, F18-T05
- **Description:**
  Create `src/api/routers/exchange_rates.py` with a new FastAPI router
  mounted at `/exchange-rates`. Endpoints:

  1. `GET /exchange-rates/current` (public)
     Returns the latest exchange rate: `{ rate_date, rate, from_currency,
     to_currency, source, age_hours }`. The `age_hours` field helps the
     frontend show a freshness indicator.

  2. `GET /exchange-rates/history` (public)
     Query param: `days` (default 30, max 365).
     Returns a list of daily rates ordered by date descending.

  3. `POST /exchange-rates/refresh` (auth required)
     Triggers a BCB PTAX fetch for today. Returns the fetched rate or
     an error message. Useful for manual refresh from the frontend admin.

  Create Pydantic schemas in `src/api/schemas/exchange_rates.py`:
  - `ExchangeRateSchema` — single rate response
  - `ExchangeRateHistoryResponse` — list of rates

  Register the router in `src/api/app.py`.

- **Acceptance Criteria:**
  - [ ] `GET /exchange-rates/current` returns latest rate
  - [ ] `GET /exchange-rates/current` returns 404 when no rates exist
  - [ ] `GET /exchange-rates/history?days=30` returns rate list
  - [ ] `POST /exchange-rates/refresh` requires API key auth
  - [ ] `POST /exchange-rates/refresh` fetches and stores rate
  - [ ] Router registered in app factory
  - [ ] Pydantic schemas with proper validation
  - [ ] Unit tests for all 3 endpoints

- **Files to touch:**
  - `src/api/routers/exchange_rates.py` (new)
  - `src/api/schemas/exchange_rates.py` (new)
  - `src/api/app.py` (register router)
  - `tests/unit/api/test_exchange_rates.py` (new)
