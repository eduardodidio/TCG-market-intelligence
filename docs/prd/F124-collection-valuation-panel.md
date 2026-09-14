# PRD — F124 Painel de coleção focado em valorização + fix link Liga

**Status:** planned · **Date:** 2026-09-13 · **Branch:** homol
**Task manifest:** `tasks/features/F124-collection-valuation-panel/F124-README.md`

## Problem

1. The paid price ("valor pago", `acquisition_price`) can only be edited on the
   collection card detail page, and the collection list API does not even
   return it — so the valuation / investment panels have little data.
2. The dashboard mixes unrelated global market stats (cards tracked,
   observations, average market price) with collection valuation.
3. "Ver na LigaMagic" on a collection card opens a different card than the one
   whose Liga price is shown (MYP link is correct).

## Users & jobs

- **Collector / investor**: "I want to type what I paid for each card right on
  the collection grid and see how much my collection appreciated."

## Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| R1 | Paid price (per copy) editable from each collection grid tile without leaving the grid | Must |
| R2 | Saved paid price is returned by list + detail APIs and feeds portfolio summary, history, P&L export, dashboard | Must |
| R3 | Clearing the paid price removes the entry from the investment totals | Must |
| R4 | P&L uses the foil price for foil entries; entries without a current price are excluded from P&L and reported as a count | Must |
| R5 | Dashboard shows only: welcome, header/freshness, collection KPIs, investment progress, collection movers, Market Trends (Trending) | Must |
| R6 | Market summary strip and market-empty CTA removed from dashboard; dashboard no longer depends on `/market/stats` | Must |
| R7 | Liga link opens exactly the page the Liga price was scraped from; fallback uses the same name as the price fetch | Must |
| R8 | README + architecture + journey diagrams updated | Must |

## Out of scope

- Removing the dedicated Market page (`/market`) or `/market/stats` endpoint.
- Network backfill of Liga URLs (populated organically by sweep/refresh).
- Changing `liga_{card_id}` / `liga_catalog_{set}_{num}` external_id formats.
- Per-lot acquisition (multiple purchase prices per entry).

## Semantics (explicit to avoid ambiguity)

- `acquisition_price` is **per copy**; `total_invested = Σ acquisition_price × quantity`
  (already implemented in `repository.get_portfolio_invested_total`).
- `total_pnl = total_current_value − invested_of_priced_entries`, where only
  entries that have BOTH a paid price and a current price participate.
  `total_invested` keeps reporting all entries with a paid price.
  `total_pnl_pct = total_pnl / invested_of_priced_entries × 100` (null when that is 0).
- New field `unpriced_card_count` = entries with paid price but no current price.

## Success metrics

- Link opens correct card for a drifted entry (entry name ≠ CardRow name).
- ≥ 1 click fewer to set a paid price (grid vs detail).
- Dashboard renders even when `/market/stats` is slow or failing.
