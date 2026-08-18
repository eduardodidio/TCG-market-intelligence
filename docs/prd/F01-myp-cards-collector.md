# PRD: F01 - MYP Cards Historical Data Collector

**Status:** Draft
**Date:** 2026-08-18
**Author:** Eduardo Rutkoski Didio

## Problem

We need a reliable way to collect and store historical pricing data for
Magic: The Gathering cards from the Brazilian market (MYP Cards) to enable
future market analytics, portfolio tracking, and opportunity scoring.

## Goals

1. Discover all Magic cards available on MYP Cards
2. Collect current prices and historical price data
3. Store data in a normalized, deduplicated database
4. Support idempotent re-execution (backfill + incremental update)
5. Handle errors gracefully without stopping the entire collection
6. Prepare architecture for multiple card sources

## Non-Goals (this phase)

- Frontend / UI
- Market analytics / indicators
- Portfolio tracking
- AI / recommendation system
- Real-time price monitoring

## Technical Analysis: MYP Cards

### Site Structure

- **Domain:** mypcards.com
- **Stack:** Server-rendered HTML (Yii2 PHP framework), Cloudflare CDN + Rocket Loader
- **robots.txt:** Allows general crawling for `User-agent: *`. Disallows `/api/`, `/admin`, `/login`, cart, orders.
  Blocks AI training crawlers (ClaudeBot, GPTBot, etc.) but allows AI search (ChatGPT-User, PerplexityBot).

### Data Access Points

#### 1. Editions/Sets Discovery
- **URL:** `GET /magic/edicoes?page={n}` (pages 1..48)
- **Data:** Links to set pages like `/magic/{set-slug}`
- **~48 pages** of editions, each listing ~30-50 sets

#### 2. Set Card Listing
- **URL:** `GET /magic/{set-slug}?page={n}`
- **Data:** Links to individual cards `/magic/produto/{id}/{slug}`
- Cards listed with thumbnail, name, price

#### 3. Search Autocomplete API (JSON)
- **URL:** `GET /produto/search?marca=magic&term={query}`
- **Returns JSON** with:
  - `idproduto` (numeric ID)
  - `nomeenproduto` (English name)
  - `nomeptproduto` (Portuguese name)
  - `codigoproduto` (SKU, e.g. `magic_ltr_748` = game_set_number)
  - `slugnomeenproduto`, `slugnomeptproduto`
  - `nomemarca` (game name)
  - `nomecategoria` (product type)
  - `qtd` (quantity available)
  - `relevance` score

#### 4. Individual Card Page (JSON-LD + HTML)
- **URL:** `GET /magic/produto/{id}/{slug}`
- **JSON-LD** `@type: Product`:
  - `name`, `sku`, `description`, `productID`
  - `offers.price`, `offers.priceCurrency` (BRL)
  - `offers.availability`
  - `previousItem`, `nextItem` (navigation)
  - `brand.name` = "Magic: The Gathering"
- **HTML price stats:**
  - Menor preco (lowest price)
  - Preco medio (average price)
  - Preco TCG (TCG Player price in BRL, converted)
  - Ultimo preco (last sold price)
  - Quantity available per seller

#### 5. Price History Page
- **URL:** `GET /magic/preco/{id}/{slug}?dias={period}`
- **Periods:** 30, 90, 180, 365, 1095 (3 years)
- **Data:** `window.precoChartConfig` JavaScript variable with:
  - `labels`: array of dates (DD/MM/YYYY format)
  - `series`: array of data series:
    - `mediana` (median price) - weekly data points
    - `tcg` (TCG Player price in BRL)
    - `ultimo` (last sold price) with `meta` array (condition/finish/language)
    - `volume` (quantity available)
  - `periodoLabel`: period description

### SKU Format Analysis

The `codigoproduto`/`sku` follows the pattern: `{game}_{set}_{number}`
- Example: `magic_ltr_748` = Magic, Lord of the Rings (LTR), card #748
- Example: `magic_dmr_412` = Magic, Dominaria Remastered (DMR), card #412
- Example: `magic_m10_146` = Magic, Magic 2010 (M10), card #146

This maps directly to Scryfall's set codes and collector numbers.

### Rate Limiting Considerations

- Site is behind Cloudflare
- No explicit rate limit headers observed
- robots.txt does not specify Crawl-delay
- Conservative approach: 1-2 requests/second with backoff on 429/403

### Data Quality Notes

- Not all cards have price history (e.g., rare variants with few sellers)
- History resolution is weekly (not daily)
- Prices are in BRL
- TCG price is converted from USD at a stated exchange rate
- `ultimo` (last sold) includes condition/finish/language metadata
- Portuguese and English names available via search API

### Limitations Found

1. No public REST API - must parse HTML + JSON-LD + inline JS
2. History is weekly resolution, not daily
3. Maximum history depth appears to be ~3 years (1095 days)
4. `precoChartConfig` not present for cards with insufficient data
5. Cloudflare may block aggressive crawling
6. robots.txt blocks `/api/` endpoint
7. Card variant data (language, condition, finish) only partially visible
   in history metadata, not as separate queryable dimensions

## Card Discovery Strategy

**Primary approach:** Iterate all editions pages, then iterate each set's card listing.

1. `GET /magic/edicoes?page=1..48` -> collect all set slugs
2. For each set, `GET /magic/{set-slug}?page=1..N` -> collect all card IDs + slugs
3. For each card, `GET /magic/produto/{id}/{slug}` -> JSON-LD + HTML for current data
4. For each card, `GET /magic/preco/{id}/{slug}?dias=1095` -> max history

**Alternative:** Search API can discover cards but requires search terms.
Better suited for targeted lookups, not full catalog discovery.

## Backfill Strategy

1. Full discovery run: all editions -> all cards
2. For each card: fetch max history (dias=1095)
3. Store each weekly observation as immutable row
4. Unique constraint on (card_variant_id, source, observed_at)
5. Re-running skips existing observations (upsert / INSERT ON CONFLICT DO NOTHING)

## Incremental Update Strategy

1. Skip full discovery (use existing catalog)
2. For each known card: fetch recent history (dias=30)
3. Insert only new observations not yet in DB
4. Optionally discover new cards in recently released sets

## Technology Choice: SQLite for MVP

**Rationale:**
- Zero infrastructure cost
- Single file, easy to backup/share
- Python built-in support (sqlite3)
- Sufficient for MVP data volume (~50K cards x 130 history points = ~6.5M rows)
- Easy migration to PostgreSQL later via SQLAlchemy
- Supports unique constraints, upsert (INSERT OR IGNORE)

**Future migration path:** SQLAlchemy ORM allows switching to PostgreSQL
with minimal code changes when scale demands it.
