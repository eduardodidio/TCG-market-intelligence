# F13 -- Scan Orchestrator

## Module: `src/collectors/scan.py`

The scan orchestrator is the central piece. It:

1. Creates a `scan_runs` row (status=running)
2. Resolves the filter to a list of cards via `repo.get_cards_for_scan()`
3. Iterates cards with `asyncio.Semaphore` (reuses snapshot_prices pattern)
4. For each card: calls `provider.fetch_current_price()`, stores observation
5. Updates `scan_runs` row with counts and status on completion/failure

### Signature

```python
async def run_scan(
    db_url: str = "sqlite:///tcg_market.db",
    scan_filter: ScanFilter | None = None,
    dry_run: bool = False,
    delay: float = 1.0,
    concurrency: int = 3,
) -> ScanRun:
```

### Key behaviors

- If `scan_filter` is None, defaults to `ScanFilter(scan_type=ScanType.COLLECTION)`
- Idempotency: skip cards that already have a `jsonld_snapshot` observation for today
- Per-card errors are logged and counted, do NOT abort the entire run
- On completion: `status=completed` (or `failed` if > 50% errors)
- Summary logged via structlog at end of run
- The function returns a `ScanRun` dataclass with all metrics filled

### Reuse from snapshot_prices.py

The core fetch-and-store loop is nearly identical to `snapshot_prices.py`.
Extract the common `_process_card()` logic or simply call the same
provider method. Do NOT duplicate the JSON-LD parsing or HTTP logic.
