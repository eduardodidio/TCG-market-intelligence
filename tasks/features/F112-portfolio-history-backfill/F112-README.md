# F112 — Portfolio History Backfill & Dashboard Activation

**Status:** planned
**Priority:** high
**Estimate:** 5 tasks, 2 waves

## Problem

The PortfolioDashboard (F105) is fully implemented but shows empty because:
1. No `portfolio_snapshots` rows exist — snapshots are only created via manual CLI (`snapshot-portfolio`), never automatically
2. No `acquisition_price` is set on `user_collection` entries — the dashboard requires `invested_card_count > 0`
3. Even if snapshots existed, only 1 day of data would exist (need `history.length > 1` for chart)

## Solution

Build a backfill pipeline + automatic snapshot mechanism:

1. **Auto-populate `acquisition_price`** on existing collection entries using the price at the time they were added (or earliest known price)
2. **Backfill synthetic portfolio snapshots** for ~30 days using historical `price_observations` data
3. **Hook snapshot creation into scan completion** so snapshots accumulate automatically going forward
4. **Add a "movers" panel** to the dashboard showing collection cards with biggest price changes (gainers/losers)
5. **CLI command for backfill** — one-shot command to seed historical data

## Data Flow

```
price_observations (existing)
  |
  v
backfill_acquisition_prices() -- sets acquisition_price = earliest known price
  |
  v
backfill_portfolio_snapshots() -- for each day in range, computes collection value
  |                                from price_observations on that date
  v
portfolio_snapshots (filled with ~30 days of history)
  |
  v
scan_hook: take_snapshot() -- runs after every scan completion
  |
  v
PortfolioDashboard -- KPIs + chart + movers now display data
```

## Tasks

| Task | Wave | Description |
|------|------|-------------|
| T01  | 0    | Backfill acquisition prices from earliest price observation |
| T02  | 0    | Backfill synthetic portfolio snapshots (~30 days) |
| T03  | 1    | Auto-snapshot hook on scan completion |
| T04  | 1    | Collection movers panel (gainers/losers from user's cards) |
| T05  | 1    | CLI command `backfill-portfolio` wrapping T01+T02 |

## Dependencies

- `price_observations` table (existing, has data from scans)
- `portfolio_snapshots` table (existing, empty)
- `user_collection` table with `acquisition_price` column (existing, nullable)
- `scan_hooks` registry (existing, F98)
- `PortfolioDashboard` component (existing, F105)

## Risks

- **Sparse price data**: not every card has daily observations. Mitigation: use forward-fill (last known price carries forward).
- **Synthetic snapshots are approximations**: clearly labeled as "estimated" in logs, not presented as authoritative historical data.
