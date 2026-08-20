# F12 Brief -- CLI, API, and Cron (T05, T07, T08, T09)

## API Schema (T05)

File: `src/api/schemas/collection.py`

New model: `SnapshotRequest(BaseModel)` with `limit: int | None = None`

## CLI Command (T07)

File: `src/cli/main.py`

New command: `snapshot-prices`
- Options: `--db`, `--limit`, `--dry-run`, `--delay`, `--concurrency`
- Calls `run_snapshot_prices()` and prints formatted summary
- Pattern: same as `sync-collection` command

## API Endpoint (T08)

File: `src/api/routers/collection.py`

New endpoint: `POST /api/v1/collection/snapshot-prices`
- Auth: `Depends(verify_api_key)` (F09 pattern)
- Body: `SnapshotRequest`
- Runs as background job via `asyncio.create_task()` + `job_tracker`
- Pattern: same as `trigger_sync` endpoint

## Cron Integration (T09)

File: `scripts/cron_update.sh`

Append snapshot-prices API call after existing update call:
- `POST /api/v1/collection/snapshot-prices` with same API key
- Non-fatal: snapshot failure does not cause cron to exit non-zero
- Inserted between update response logging and health check
