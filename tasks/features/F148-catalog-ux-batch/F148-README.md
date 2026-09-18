# F148 — Catalog UX Batch

**Status:** planned
**Created:** 2026-09-18
**Feature ID:** F148

## Overview

Five catalog improvements: duplicate card disambiguation, enqueue price fetch
from catalog, bulk refresh collection prices, import card via Liga link, and
default sort by price descending.

## Tasks

| Task | Wave | Description |
|------|------|-------------|
| F148-T01 | 0 | Default sort by price desc (NULLS LAST) |
| F148-T02 | 0 | Duplicate card disambiguation (collector_number + type_line) |
| F148-T03 | 0 | Enqueue price fetch from catalog (per-card) |
| F148-T04 | 1 | Bulk refresh collection prices |
| F148-T05 | 1 | Import card via Liga link |

## Wave Plan

### Wave 0 (parallel — no dependencies)
- **T01**: Backend + frontend sort default change (trivial, no new endpoints)
- **T02**: Frontend-only — show collector_number + type_line in CatalogCardTile
- **T03**: Already exists per-card refresh button — verify it works for unpriced cards too (the button exists but may need UX adjustment for unpriced cards)

### Wave 1 (parallel — depends on price request system from Wave 0 verification)
- **T04**: New endpoint + frontend button for bulk collection refresh
- **T05**: New endpoint + frontend component for Liga link import

## Architecture Notes

- Price requests use `PriceUpdateRequestRow` table (status: pending→processing→completed/failed)
- Catalog prices join via `'liga_' || CAST(c.id AS TEXT)` on price_observations
- Credit system: 1 credit per card refresh, deducted upfront
- Liga URLs: `https://www.ligamagic.com.br/?view=cards/card&card={name}[&ed={set}]`
- Catalog cards have collector_number + type_line available but not displayed in tiles
