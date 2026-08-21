# F18-T06: CLI Command — update-exchange-rate

- **Wave:** 1
- **Status:** done
- **Depends on:** F18-T02, F18-T04
- **Description:**
  Add a new Click command `update-exchange-rate` to `src/cli/main.py`:

  ```
  tcg update-exchange-rate [--db URL] [--date YYYY-MM-DD] [--backfill-days N]
  ```

  Behavior:
  - Default (no flags): fetches today's PTAX rate and stores it.
  - `--date`: fetches the rate for a specific date.
  - `--backfill-days N`: fetches rates for the last N days (uses the
    BCB period endpoint for efficiency). Default: 0 (just today).
  - Idempotent: running twice for the same date updates the rate if
    it changed (upsert).
  - Logs the rate fetched and stored.
  - Exit code 0 on success, 1 on failure (BCB unreachable, etc.).

  This command is designed to be called by cron once per day, after
  market close (~18:00 BRT).

- **Acceptance Criteria:**
  - [ ] Command registered in CLI group
  - [ ] Default invocation fetches and stores today's rate
  - [ ] `--backfill-days 30` populates 30 days of history
  - [ ] `--date` fetches a specific date
  - [ ] Handles weekends (BCB returns no data) gracefully
  - [ ] Logs clearly: date, rate fetched, stored/updated
  - [ ] Unit test for command registration
  - [ ] Integration test with mocked BCB client

- **Files to touch:**
  - `src/cli/main.py`
  - `tests/unit/cli/test_cli_exchange_rate.py` (new)
