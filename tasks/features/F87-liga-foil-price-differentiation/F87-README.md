# F87 — Liga Foil Price Differentiation

**Status:** planned
**Owner:** @architect
**PRD:** inline

## Problem

Foil cards in the user's collection are showing the same price as non-foil
versions. The Liga parser already extracts foil prices (`parse_card_prices`
returns `foil.low/mid/high`), but the scan pipeline ignores them — it only
uses `normal.low`. Foil cards typically cost 2-10x more than their non-foil
counterparts, so this is a significant data accuracy issue.

## Current State

| Layer | Foil Support | Notes |
|-------|-------------|-------|
| Liga parser | YES | `_extract_foil_section()` + foil low/mid/high |
| `Finish` enum | YES | `domain/models.py` — NORMAL, FOIL, ETCHED |
| Scan pipeline | NO | `_fetch_price_liga` uses only `normal.low` |
| PriceObservation | NO | No finish column; external_id has no foil suffix |
| UserCollectionRow | PARTIAL | `extras` field may contain "Foil" from CSV |
| `get_latest_prices_batch` | NO | Single price per card, no variant |
| Frontend | NO | Single `latest_price` per entry |

## Strategy

**External ID suffix approach** (no schema migration needed):

1. Detect foil entries via `extras` field parsing (contains "Foil")
2. When scanning/refreshing a foil entry, store the foil price with
   external_id = `"liga_{card_id}_foil"` (vs `"liga_{card_id}"` for normal)
3. `get_latest_prices_batch` checks entry's foil status and looks up the
   correct external_id variant
4. Frontend shows a foil badge and the correct foil price

This avoids adding columns to PriceObservationRow and uses the existing
unique constraint `(source, external_id, observed_at)` naturally.

## Wave Structure

- **Wave 0** (3 tasks, parallel): Backend foil detection + price storage + price lookup
- **Wave 1** (1 task, depends on Wave 0): Frontend foil display

## Tasks

| Task | Wave | Description |
|------|------|-------------|
| F87-T01 | 0 | Foil detection from collection extras field |
| F87-T02 | 0 | Scan/refresh pipeline stores foil prices separately |
| F87-T03 | 0 | get_latest_prices_batch foil-aware lookup |
| F87-T04 | 1 | Frontend foil badge + foil price display |

## Dependencies

- None (builds on existing Liga parser foil extraction)

## Risks

- Liga HTML foil section detection is heuristic (keyword-based). If Liga
  changes their layout, foil parsing may break. Mitigated by existing
  test fixtures.
- `extras` field parsing is fragile (plain string). Consider adding a
  dedicated `finish` column to UserCollectionRow in a future feature.
