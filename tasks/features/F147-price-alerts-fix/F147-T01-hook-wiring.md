# F147-T01: Wire scan hooks to CLI liga-sweep

**Wave:** 0 (sequential — must ship before frontend work)
**Estimate:** Small

## User Story

As a user with price alerts configured, I want my alerts to be checked
after the daily scan runs, so that I get notified when card prices cross
my target thresholds.

## Problem

`run_liga_sweep()` in `src/collectors/liga_sweep.py` does not accept an
`on_complete` callback. The CLI `liga-sweep` command (used by
`daily-scan.bat`) therefore never fires scan hooks. Alert checking,
cache invalidation, trending invalidation, and portfolio snapshots all
silently skip on the primary production scan path.

Meanwhile, `run_liga_scan()` and `run_scan()` (called from API endpoints)
DO accept and invoke `on_complete`. The CLI `liga-sweep` is the only
scan path that skips hooks entirely.

## Dev Notes

### Changes to `src/collectors/liga_sweep.py`

1. Add `on_complete: Callable[[ScanRun, list[str]], None] | None = None`
   parameter to `run_liga_sweep()`.
2. At the end of the sweep (after all batches complete, before returning
   `LigaSweepResult`), if `on_complete` is not None and there are
   processed external_ids, call `on_complete(scan_run, external_ids)`.
3. The sweep currently does not create a `ScanRun` object. Either:
   - Create a minimal `ScanRun` for the callback (preferred — matches
     the pattern in `liga_scan.py`), OR
   - Use a lightweight wrapper that satisfies the hook signature.
4. Collect the list of `external_id` strings that were successfully
   priced during the sweep (these are already tracked internally as
   `liga_{card_id}` strings).

### Changes to `src/cli/main.py`

1. In the `liga_sweep` command (~line 1170), import and wire the hooks:
   ```python
   from src.services.scan_hooks import default_registry
   from src.services.alert_checker import make_alert_checker_hook
   from src.database.repository import Repository

   # Register alert checker hook for CLI path
   repo = Repository(db_url)
   alert_hook = make_alert_checker_hook(repo)
   default_registry.register(alert_hook)

   result = asyncio.run(
       run_liga_sweep(
           ...,
           on_complete=default_registry.notify,
       )
   )
   ```
2. Apply the same pattern to the `catalog_scan` command (~line 2076).
3. Be careful NOT to register hooks multiple times if the registry is
   module-level singleton. Either check if already registered, or
   register fresh each CLI invocation (CLI runs once and exits, so
   duplicates are not an issue).

### Important constraints

- `run_liga_sweep` processes cards in batches. The `on_complete` callback
  should fire ONCE at the end with ALL processed external_ids, not per
  batch. This matches how `run_liga_scan` works.
- The daily-scan.bat also runs `snapshot-portfolio` and
  `process-price-requests` after liga-sweep. The portfolio snapshot hook
  will now also fire from liga-sweep's on_complete, but that is
  idempotent (upserts by date), so double-snapshot is safe.

## Testing

### Unit tests
- Test that `run_liga_sweep()` calls `on_complete` with correct args
  when cards are processed (mock the Liga provider).
- Test that `on_complete` is NOT called when `dry_run=True`.
- Test that `on_complete` is NOT called when no cards were processed.

### Integration verification
- Run `python -m src.cli.main liga-sweep --dry-run` — should not crash
  with new parameter.
- Create a price alert, run a manual liga-sweep, verify alert triggers.

## Acceptance Criteria
- [ ] `run_liga_sweep()` accepts optional `on_complete` callback
- [ ] CLI `liga-sweep` command registers alert checker hook and passes
      `on_complete=default_registry.notify`
- [ ] CLI `catalog scan` command does the same
- [ ] Existing tests pass; new tests cover the callback path
- [ ] Alert checker fires after CLI liga-sweep completes
