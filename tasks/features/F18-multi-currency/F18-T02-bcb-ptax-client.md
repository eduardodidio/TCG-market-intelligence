# F18-T02: BCB PTAX API Client

- **Wave:** 0
- **Status:** done
- **Depends on:** none
- **Description:**
  Create `src/providers/bcb/client.py` with an async function to fetch the
  daily USD/BRL exchange rate from the BCB PTAX API. The endpoint is:

  ```
  GET https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/
      CotacaoDolarDia(dataCotacao=@d)?@d='MM-DD-YYYY'&$format=json
  ```

  The function should:
  1. Accept a `date` parameter (defaults to today).
  2. Make an HTTP GET request (use `httpx` — no Cloudflare on BCB).
  3. Parse the JSON response and extract `cotacaoVenda` (sell rate).
  4. Return a domain `ExchangeRate` dataclass or `None` if no data.
  5. Handle weekends/holidays (BCB returns empty `value` array).
  6. Include a `fetch_range(start_date, end_date)` method for backfilling
     historical rates (calls `CotacaoDolarPeriodo` endpoint).
  7. Use structlog for logging.
  8. Respect rate limits (add configurable delay between requests).

  Also create `src/providers/bcb/__init__.py`.

- **Acceptance Criteria:**
  - [ ] `fetch_daily_rate(date)` returns ExchangeRate or None
  - [ ] `fetch_rate_range(start, end)` returns list of ExchangeRate
  - [ ] Handles HTTP errors gracefully (returns None, logs error)
  - [ ] Handles empty BCB responses (weekends/holidays)
  - [ ] Unit tests with mocked HTTP responses (success, empty, error)
  - [ ] No new dependencies required (httpx already in project or use existing curl_cffi)

- **Files to touch:**
  - `src/providers/bcb/__init__.py` (new)
  - `src/providers/bcb/client.py` (new)
  - `tests/unit/providers/bcb/test_client.py` (new)
