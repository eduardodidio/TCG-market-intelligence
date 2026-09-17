# F132-T02: Verify/Fix process-price-requests in daily-scan.bat

**Wave:** 0
**Status:** pending
**Depends on:** none

## User Story

As a platform operator, I want the daily scan automation to process all
pending price requests automatically, so that users who queued price
updates during the day get their results by the next morning.

## Current State

`daily-scan.bat` already contains `process-price-requests --limit 100`
between `liga-sweep` and `snapshot-portfolio`. This ordering is correct:

```batch
python -m src.cli.main liga-sweep --max-age-days 1
python -m src.cli.main process-price-requests --limit 100
python -m src.cli.main snapshot-portfolio
```

The brief indicated this was missing, but the current codebase already has it.

## Dev Notes

### 1. Verify current setup is correct

- Confirm the command ordering is optimal: liga-sweep first (bulk update),
  then process-price-requests (individual user requests), then snapshot.
- Confirm `--limit 100` is sufficient. If the queue can accumulate more
  than 100 requests/day, increase to `--limit 500` or remove the limit.

### 2. Add error handling to daily-scan.bat

Currently all three commands run sequentially with no error checking. If
`liga-sweep` fails (e.g., Liga down), the remaining commands should still
run. Add `|| echo [WARN] liga-sweep failed` patterns:

```batch
python -m src.cli.main liga-sweep --max-age-days 1 || echo [WARN] liga-sweep failed
python -m src.cli.main process-price-requests --limit 500 || echo [WARN] process-price-requests failed
python -m src.cli.main snapshot-portfolio || echo [WARN] snapshot-portfolio failed
```

### 3. Increase --limit

Change `--limit 100` to `--limit 500`. With a 2-second delay between
requests, 500 requests would take ~17 minutes. This is acceptable for a
daily batch job. Users rarely queue more than a few dozen per day, so this
is a safety margin.

### 4. Add logging output

Add timestamp echo before and after `process-price-requests` for easier
debugging when reviewing Task Scheduler history:

```batch
echo  [%time%] Processing price request queue...
python -m src.cli.main process-price-requests --limit 500 || echo [WARN] process-price-requests failed
echo  [%time%] Price request queue done.
```

## Testing

### Manual
- Run `daily-scan.bat` locally and confirm all three commands execute in
  order, with proper output.
- Verify that if one command fails (e.g., pass an invalid flag), the
  remaining commands still run.

### Automated
- No automated tests for .bat files. This is a configuration/ops task.
- The CLI `process-price-requests` command already has backend tests
  (the CLI invokes repo methods that are tested).

## Acceptance Criteria

- [ ] `daily-scan.bat` runs `process-price-requests` with `--limit 500`
- [ ] Each command has `|| echo [WARN]` error fallback so subsequent steps run
- [ ] Timestamp logging around price request processing step
- [ ] Command ordering: liga-sweep -> process-price-requests -> snapshot-portfolio
