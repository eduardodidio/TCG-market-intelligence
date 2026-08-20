# F12 Brief -- Overview

## Problem

MYP Cards moved price history behind authentication (2026-08-20). The
`/magic/preco/{id}/{slug}?dias=N` endpoint returns 302 to login. The
`window.precoChartConfig` JS variable no longer exists on public pages.
Result: zero new price observations can be collected.

## Solution

Extract current prices from JSON-LD `offers.price` on public MYP product
pages and build price history organically via daily snapshots. No auth
required. After 30 days of daily runs, analytics have sufficient data.

## What JSON-LD Provides

- `offers.price`: current price in BRL (InStock: marketplace lowest; OutOfStock: TCG converted)
- `offers.availability`: InStock / OutOfStock (schema.org URL)
- `offers.priceCurrency`: "BRL"
- Some cards have price=0 (no data) -- these are skipped

## Constraints

- Collection cards only (user_collection.card_id IS NOT NULL)
- Existing `price_observations` table, no schema changes
- Source marker: `jsonld_snapshot` (distinct from old `myp` observations)
- Idempotent: skip if card+date already exists
- Rate limiting: asyncio.Semaphore(3) + 1s delay
- No new dependencies
