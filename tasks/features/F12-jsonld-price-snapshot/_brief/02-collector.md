# F12 Brief -- Collector (T04)

## Snapshot Collector

File: `src/collectors/snapshot_prices.py` (new)

Main function: `run_snapshot_prices(db_url, limit, dry_run, delay, concurrency) -> SnapshotSummary`

### Flow

1. Load linked collection entries via new `repo.get_linked_collection_with_source("myp")`
2. For each entry (with Semaphore concurrency):
   a. Check idempotency: `repo.has_snapshot_for_date(external_id, today)` -- skip if True
   b. Fetch price: `provider.fetch_current_price(external_id, slug)`
   c. Skip if price is None (zero/missing)
   d. Create `HistoricalPrice(source="jsonld_snapshot", external_id, observed_at=today, median_price=price)`
   e. Store via `repo.insert_price_observations([observation])`
3. Return SnapshotSummary with counts

### New Repository Methods

1. `get_linked_collection_with_source(source: str) -> list[dict]`
   - JOIN user_collection + source_cards on card_id
   - Returns: entry_id, card_id, external_id, slug (from URL), url
   - Filter: card_id IS NOT NULL, source_cards.source = source

2. `has_snapshot_for_date(external_id: str, obs_date: date) -> bool`
   - Query: SELECT 1 FROM price_observations WHERE source="jsonld_snapshot" AND external_id=? AND observed_at=?

### Key Design Decisions

- Use `source="jsonld_snapshot"` to keep old `myp` observations separate
- Store price as `median_price` (consistent with existing analytics which read median_price)
- The slug is extracted from the source_card URL: `url.rsplit("/", 1)[-1]`
