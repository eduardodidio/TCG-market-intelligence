# F13 -- CLI & API

## CLI Commands

### `scan` command

```
python -m src.cli.main scan [OPTIONS]
```

Options:
- `--db` -- database URL (default: sqlite:///tcg_market.db)
- `--type` -- scan type: collection (default), set, format, custom
- `--set` -- set code filter (repeatable or comma-separated)
- `--format` -- format filter (standard, modern, legacy, etc.)
- `--rarity` -- rarity filter (repeatable or comma-separated)
- `--card-ids` -- comma-separated card IDs for custom scan
- `--limit` -- max cards to process
- `--dry-run` -- don't write to database
- `--delay` -- seconds between requests (default 1.0)
- `--concurrency` -- max concurrent requests (default 3)

Output: prints scan summary (same style as snapshot-prices).

### `scan-history` command

```
python -m src.cli.main scan-history [OPTIONS]
```

Options:
- `--db` -- database URL
- `--limit` -- max rows (default 20)
- `--type` -- filter by scan type
- `--status` -- filter by status

Output: formatted table with columns: ID, Type, Status, Cards, Processed,
Failed, Observations, Started, Elapsed.

## API Endpoints

### `POST /api/v1/scans`

Request body:
```json
{
  "scan_type": "collection",
  "set_codes": ["dmr", "one"],
  "limit": 50,
  "dry_run": false
}
```

Response: `{ "scan_id": 1, "status": "running" }`

Runs in background thread (same pattern as existing sync/snapshot endpoints).
Requires API key auth.

### `GET /api/v1/scans`

Query params: `limit`, `offset`, `scan_type`, `status`

Response: `{ "scans": [...], "total": N }`

No auth required (read-only).

### `GET /api/v1/scans/{scan_id}`

Response: full scan run details including error_summary.

No auth required (read-only).
