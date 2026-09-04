# F103 — Offline Card Catalog (Scryfall + Liga Prices)

**Status:** planned
**Priority:** P1
**Estimated tasks:** 7
**Waves:** 3

## Summary

Catálogo offline completo de todas as cartas de Magic: The Gathering já
lançadas, usando Scryfall bulk data como fonte autoritativa e LigaMagic
como fonte de preços. O scan de preços é **manual** via CLI — o usuário
decide quando e quais sets escanear.

## Problem

Hoje o sistema só conhece cartas que foram adicionadas manualmente à
coleção do usuário. Não existe um catálogo completo para browsing,
comparação de preços, ou descoberta de cartas fora da coleção.

## Solution

1. **Scryfall bulk data seed** — baixar o arquivo `default_cards` do
   Scryfall (~150MB JSON), parsear e inserir todas as cartas únicas no
   banco local (`cards` + `source_cards` para Liga).
2. **CLI commands** — `catalog seed` (download + seed), `catalog scan`
   (Liga price sweep por set), `catalog stats` (contagem rápida).
3. **Catalog browse API** — endpoints REST para buscar/filtrar/paginar o
   catálogo completo (distinto da coleção do usuário).
4. **Frontend Catalog page** — nova página `/catalog` com busca, filtros
   (set, cor, raridade, faixa de preço), e grid de cartas.

## Non-goals (this iteration)

- Sync automático/scheduled do catálogo (manual-only)
- Price history charts na página de catálogo (reusa existing para cards na collection)
- Importação de catálogos de outros jogos (Pokemon, Yu-Gi-Oh) — Magic only
- Deck-building direto do catálogo

## Architecture

```
Scryfall bulk JSON → ScryfallCatalogSeeder → cards table + source_cards (liga)
                                          ↓
CLI: `catalog seed`  ←──────────────────→ ScryfallCatalogSeeder
CLI: `catalog scan --set <code>`  ←─────→ liga_sweep (existing)
CLI: `catalog stats`  ←────────────────→ Repository queries
                                          ↓
API: GET /catalog/cards  ←──────────────→ CatalogService → Repository
API: GET /catalog/sets   ←──────────────→ CatalogService → Repository
API: GET /catalog/stats  ←──────────────→ CatalogService → Repository
                                          ↓
Frontend: /catalog page  ←──────────────→ API calls
```

## Data Model Impact

- `cards` table: ~30k–80k new rows (one per unique card printing)
- `source_cards` table: same number of rows (source=`liga`, external_id=`liga_catalog_{set}_{cn}`)
- No new tables required — reuses existing schema
- New columns on `cards`: `rarity` (String(5)), `color_identity` (String(20)),
  `mana_cost` (String(50)), `type_line` (String(200)), `image_uri` (String(500))

## Risks

- Scryfall bulk file is ~150MB; download pode falhar — implementar resume/retry
- ~30k–80k inserts pode ser lento — usar batch upsert com chunks de 500
- Liga scan de todo o catálogo levaria semanas — scan é por set, manual
- Novas colunas no `cards` requerem migration cuidadosa (nullable, sem breaking change)

## Waves

### Wave 0 — Schema + Seeder (tasks T01–T03)
- T01: Extend cards table schema (new columns)
- T02: Scryfall bulk data downloader + parser
- T03: Catalog seeder (batch upsert cards + source_cards)

### Wave 1 — CLI + Scan (tasks T04–T05)
- T04: CLI `catalog` command group (seed, scan, stats)
- T05: Adapt liga_sweep for catalog-mode (scan cards without collection)

### Wave 2 — API + Frontend (tasks T06–T07)
- T06: Catalog REST API endpoints
- T07: Frontend Catalog page
