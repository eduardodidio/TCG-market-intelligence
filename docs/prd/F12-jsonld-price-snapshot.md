# PRD: F12 - JSON-LD Price Snapshot

**Status:** Delivered
**Date:** 2026-08-20
**Author:** Eduardo Rutkoski Didio
**Prerequisite:** F10 (Collection-Centric Pivot), F11 (Post-F10 Operationalization)

## Problem

MYP Cards moved their price history endpoint (`/magic/preco/{id}/{slug}?dias=N`)
behind authentication on 2026-08-20. The endpoint now returns a 302 redirect to
the login page, and the `window.precoChartConfig` JS variable no longer exists on
public pages. This was discovered during F11 sync operations, where 0 new price
observations were collected despite 124 cards being linked.

Without price history data, the analytics engine (MA, ATH/ATL, volatility,
momentum) has no new inputs, and the dashboard price charts will stagnate
indefinitely.

## Solution

Extract current prices from the JSON-LD `@type: Product` / `offers.price`
structured data embedded in MYP product pages. This data remains publicly
accessible without authentication.

Instead of fetching historical time series in a single request, the system
builds price history organically by taking a daily snapshot of each card's
current price. After 7 days of daily runs, the price chart shows a trend line.
After 30 days, the analytics engine has sufficient data points for moving
averages and volatility calculations.

## Scope

| Component | Change |
|-----------|--------|
| `src/domain/models.py` | New `JsonLdPrice` and `SnapshotSummary` dataclasses |
| `src/parsers/myp.py` | New `parse_jsonld_price()` function |
| `src/providers/myp/provider.py` | New `fetch_current_price()` method |
| `src/collectors/snapshot_prices.py` | New file -- daily snapshot collector |
| `src/cli/main.py` | New `snapshot-prices` CLI command |
| `src/api/schemas/collection.py` | New `SnapshotRequest` Pydantic model |
| `src/api/routers/collection.py` | New `POST /api/v1/collection/snapshot-prices` endpoint |
| `scripts/cron_update.sh` | Appended snapshot-prices API call after existing daily update |
| `frontend/src/components/PriceChart.tsx` | Sparse data empty-state improvement |

## Constraints

- **Collection-only:** snapshots are taken only for cards linked to the user's
  collection (`user_collection.card_id IS NOT NULL`), not the entire MYP catalog
- **No schema changes:** observations are stored in the existing
  `price_observations` table with `source="jsonld_snapshot"`
- **Idempotent:** if a card already has a `jsonld_snapshot` observation for
  today's date, it is skipped
- **No new dependencies:** uses existing `curl_cffi`, `beautifulsoup4`, and
  `structlog`
- **Rate-limited:** respects MYP rate limits via `asyncio.Semaphore` with
  configurable concurrency (default 3) and delay (default 1s)

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-01 | `parse_jsonld_price()` extracts `price`, `currency`, and `availability` from JSON-LD `offers` block |
| FR-02 | `fetch_current_price()` fetches a product page and returns a `JsonLdPrice` |
| FR-03 | Snapshot collector iterates linked collection entries and stores one observation per card per day |
| FR-04 | Observations use `source="jsonld_snapshot"` and store the price in `median_price` |
| FR-05 | Idempotency: skip if `external_id + date` already has a `jsonld_snapshot` observation |
| FR-06 | `snapshot-prices` CLI command with `--limit`, `--dry-run`, `--delay`, `--concurrency` options |
| FR-07 | `POST /api/v1/collection/snapshot-prices` endpoint with API key authentication |
| FR-08 | Cron script calls snapshot-prices endpoint after existing daily update |
| FR-09 | Frontend PriceChart handles sparse data (fewer than 2 data points) without breaking |

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-01 | Concurrency controlled via `asyncio.Semaphore` (default 3) |
| NFR-02 | Per-card errors are logged and do not abort the entire run |
| NFR-03 | Summary logged at end of run with counts for fetched, stored, skipped, errors |
| NFR-04 | No new Python or npm dependencies introduced |

## Out of Scope

- Fetching historical price data from MYP (endpoint is auth-walled)
- Alternative price sources (Liga Magic, CardMarket, TCGPlayer)
- Multi-user support
- Alerting on price changes
- Caching or deduplication across sources

## Success Metrics

| Metric | Target |
|--------|--------|
| Daily observations stored | 1 per linked collection card per day |
| Chart populated | Visible trend line after 7+ daily runs |
| Analytics functional | MA(7), MA(30) computable after 30 daily runs |
| Error rate | < 5% of linked cards per run |

## Acceptance Criteria

1. `parse_jsonld_price()` extracts price, currency, availability from JSON-LD
2. `fetch_current_price()` fetches product page and returns `JsonLdPrice`
3. Snapshot collector stores observations with `source="jsonld_snapshot"`
4. Idempotency: re-running on same day inserts 0 new observations
5. `snapshot-prices` CLI command works with `--limit` and `--dry-run`
6. `POST /api/v1/collection/snapshot-prices` requires API key, returns job ID
7. Cron script calls snapshot-prices after existing update
8. Frontend PriceChart handles sparse data gracefully
9. All existing tests pass, new tests added for parser/collector/CLI/API
10. Coverage >= 90%
