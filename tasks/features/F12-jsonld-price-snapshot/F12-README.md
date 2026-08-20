# F12 -- JSON-LD Price Snapshot

**Status:** done

## Summary

MYP Cards moved price history behind authentication (2026-08-20). The old
`/magic/preco/{id}/{slug}?dias=N` endpoint now returns 302 to login. The
`precoChartConfig` JS variable no longer exists on public pages, so zero
new price observations can be collected with the current provider.

This feature extracts current prices from JSON-LD `offers.price` on MYP
product pages (public, no auth required) and builds price history
organically via daily snapshots. After 30 days of daily runs, analytics
(MA, ATH/ATL, volatility) will have sufficient data points.

The collector operates on collection cards only (cards with
`user_collection.card_id` set), stores observations in the existing
`price_observations` table with source marker `jsonld_snapshot`, and is
idempotent (skip if card+date already has a snapshot observation).

## Architecture Impact

- `src/domain/models.py` -- new `JsonLdPrice` dataclass, new `SnapshotSummary` dataclass
- `src/parsers/myp.py` -- new `parse_jsonld_price()` function
- `src/providers/myp/provider.py` -- new `fetch_current_price()` method
- `src/collectors/snapshot_prices.py` -- **new file**, daily snapshot collector
- `src/cli/main.py` -- new `snapshot-prices` CLI command
- `src/api/schemas/collection.py` -- new `SnapshotRequest` Pydantic model
- `src/api/routers/collection.py` -- new `POST /api/v1/collection/snapshot-prices` endpoint
- `scripts/cron_update.sh` -- append snapshot-prices API call after existing daily update
- `frontend/src/components/PriceChart.tsx` -- sparse data empty-state improvement

No schema changes. No new dependencies. No behavioral changes to existing code.

## Wave Manifest

| Wave | Tasks                    | Description                                     |
|------|--------------------------|-------------------------------------------------|
| 0    | F12-T01, F12-T02         | Domain model + Parser (foundation, parallel)     |
| 1    | F12-T03                  | Provider method (depends on domain + parser)     |
| 2    | F12-T04, F12-T05, F12-T06 | Collector + API schema + Frontend (parallel)    |
| 3    | F12-T07, F12-T08, F12-T09 | CLI + API endpoint + Cron (parallel)            |
| 4    | F12-T10                  | Documentation (PRD, diagrams, README)            |

## Global Acceptance Criteria

- [x] `parse_jsonld_price()` extracts price, currency, availability from JSON-LD
- [x] `fetch_current_price()` fetches product page and returns `JsonLdPrice`
- [x] Snapshot collector iterates linked collection entries and stores observations
- [x] Observations stored with `source="jsonld_snapshot"` in `price_observations`
- [x] Idempotency: skip if card+date already has a `jsonld_snapshot` observation
- [x] `snapshot-prices` CLI command with `--limit` and `--dry-run` flags
- [x] `POST /api/v1/collection/snapshot-prices` endpoint with API key auth
- [x] Cron script calls snapshot-prices endpoint after existing daily update
- [x] Frontend PriceChart handles sparse data without breaking
- [x] All existing tests still pass (604+ backend, 187+ frontend)
- [x] New unit tests for parser, collector, CLI, and API endpoint
- [x] Coverage >= 90%
- [x] README.md updated with F12 delivery notes

## Diagrams

- `docs/diagrams/F12-architecture.mmd` -- data flow: collection DB -> fetch product page -> parse JSON-LD -> store observation
- `docs/diagrams/F12-journey.mmd` -- operator journey: CLI/API trigger -> snapshot run -> dashboard verification
