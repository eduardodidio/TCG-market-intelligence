# F124 — Painel de coleção focado em valorização + fix link Liga

**Status:** planned
**Created:** 2026-09-13
**Branch:** homol
**PRD:** `docs/prd/F124-collection-valuation-panel.md`
**ADR:** `docs/adr/0012-liga-fetched-url-persistence.md`
**Brief (sharded):** `_brief/00-overview.md`, `_brief/01-paid-price.md`, `_brief/02-dashboard.md`, `_brief/03-liga-link.md`

## Goal

Turn the collection panel into a valuation/investment panel: the user sets
the paid price (per copy) directly from each collection grid tile and that
value correctly feeds portfolio summary, P&L and a new dashboard investment
progress block; the dashboard drops global market stats that are not about
the user's collection (keeping Market Trends); and the "Ver na LigaMagic"
link opens exactly the page the Liga price was scraped from (MYP parity).

## Architecture impact

| Layer | Modules |
|-------|---------|
| DB | new table `liga_card_urls` (`LigaCardUrlRow`, via `create_all`) |
| Repository | `upsert_liga_card_url`, `get_liga_card_url` |
| Providers | new `src/providers/liga/urls.py`; `provider.py` captures `page.url`, returns `prices["page_url"]` |
| Collectors / CLI | `liga_sweep.py`, `scan.py`, `cli/main.py` record URL |
| API | `collection.py` (list/detail acquisition fields, portfolio-summary P&L, refresh-liga writer, detail Liga link), `cards.py` (writer + `ligamagic_url`), `card_search.py`, schemas |
| Frontend | `Dashboard.tsx` slim, new `DashboardInvestmentSummary.tsx`, new `PaidPriceQuickEdit.tsx`, `MyCollection.tsx`, `PortfolioDashboard.tsx`, `AcquisitionPriceInput.tsx`, `CardDetail.tsx`, `api/collection.ts`, `types/api.ts`, i18n |
| Docs | README, `docs/diagrams/F124-architecture.mmd`, `docs/diagrams/F124-journey.mmd` |

## Wave manifest

- **Wave 0**: F124-T01, F124-T02, F124-T03, F124-T05
- **Wave 1**: F124-T04, F124-T06, F124-T09
- **Wave 2**: F124-T07, F124-T08
- **Wave 3**: F124-T10

| Task | Summary | Type | Wave | Depends on |
|------|---------|------|------|------------|
| T01 | Liga URL helpers (`urls.py`) + provider `page_url` capture | backend | 0 | — |
| T02 | `LigaCardUrlRow` model + repository upsert/get | backend | 0 | — |
| T03 | Collection API: acquisition fields in list/detail + portfolio P&L fix (foil, unpriced) | backend | 0 | — |
| T05 | `PaidPriceQuickEdit` component + clear-to-null fix + **sole owner of all new F124 i18n keys** | frontend | 0 | — |
| T04 | `DashboardInvestmentSummary` component (consumes `dashboard.investment*` i18n from T05) | frontend | 1 | T05 |
| T06 | Record fetched Liga URL in all Liga price writers | backend | 1 | T01, T02, T03 |
| T09 | Integrate quick edit into collection grid + portfolio refresh | frontend | 1 | T05 |
| T07 | Serve stored Liga URL (collection detail, card detail, web search) + `CardDetail.tsx` | backend+frontend | 2 | T01, T02, T06 |
| T08 | Slim `Dashboard.tsx` + mount investment summary | frontend | 2 | T04 |
| T10 | README + diagrams + full regression (pytest, vitest, build, ruff) | docs/test | 3 | all |

## Wave 0 setup / permissions

No new dependencies (pip or npm), no CI changes, no migrations (new table
comes from `create_all`), no new directories outside the ones that already
exist (`src/providers/liga/`, `frontend/src/components/`, `docs/diagrams/`).
Commands used by all waves are the standard ones from `CLAUDE.md`
(`pytest`, `npm test`, `npm run build`, `ruff check src/`).

## File conflict map

| File | Tasks | Resolution |
|------|-------|-----------|
| `src/api/routers/collection.py` | T03 (list/detail acq fields, portfolio-summary), T06 (refresh-liga writer), T07 (detail Liga link) | Sequential: W0 → W1 → W2 |
| `src/api/routers/cards.py` | T06 (refresh writer), T07 (detail `ligamagic_url`) | W1 → W2 |
| `src/api/schemas/collection.py` | T03 only | — |
| `src/providers/liga/provider.py` | T01 only | — |
| `src/database/models.py`, `repository.py` | T02 only | — |
| `frontend/src/types/api.ts` | T04 (PortfolioSummary optional field, W1), T07 (CardDetail `ligamagic_url`, W2) | W1 → W2 |
| `frontend/src/api/collection.ts` | T05 only | — |
| i18n `en.json` / `pt-BR.json` | **T05 only** (sole owner of all new F124 keys: `collection.paidPrice*` + `dashboard.investment*`) | No collision — T04 consumes the `dashboard.investment*` keys in W1 (added by T05 in W0) |
| `frontend/src/pages/MyCollection.tsx`, `PortfolioDashboard.tsx` | T09 only | — |
| `frontend/src/pages/Dashboard.tsx` | T08 only | — |

## Global acceptance criteria

- [ ] AC1 Paid price editable from every collection grid tile; list + detail APIs return it; value feeds portfolio summary / dashboard.
- [ ] AC2 Clearing the paid price persists `null`.
- [ ] AC3 P&L uses foil price for foil entries; unpriced entries excluded from P&L and counted in `unpriced_card_count`.
- [ ] AC4 Dashboard = collection/valuation + Trending only; `market-summary-strip` and `market-empty` gone; no `/market/stats` call from Dashboard.
- [ ] AC5 Liga link = URL the Liga price was fetched from (stored in `liga_card_urls`); fallback name = same name used for the fetch; invalid/foreign URLs never served.
- [ ] AC6 `pytest tests/` green with coverage not decreasing for touched modules; `npm test` + `npm run build` green; `ruff check src/` clean.
- [ ] AC7 README updated; `docs/diagrams/F124-architecture.mmd` and `docs/diagrams/F124-journey.mmd` created.

## Diagrams

- `docs/diagrams/F124-architecture.mmd` — owner T10 (stub in T10)
- `docs/diagrams/F124-journey.mmd` — owner T10 (stub in T10)

## Risks / notes

- Liga URL coverage grows with each sweep (≤ `max_age_days`, default 7); fallback covers the gap (documented in README).
- `acquisition_price` is stored in BRL; per-tile P&L chip hidden for non-BRL display currency.
- Semantics change of `total_pnl` / `total_pnl_pct` (priced-only denominator) — existing `tests/api/test_collection_portfolio.py` expectations may need updating; justify in the test docstring.
