# F124 — Painel de coleção focado em valorização + fix link Liga — Overview

**Branch:** `homol` (promote to `main` only with user approval)
**Created:** 2026-09-13

## Problem

The collection panel mixes investment/valuation content with global market
stats that have nothing to do with the user's cards. The "valor pago" (paid
price / acquisition price) can only be edited deep inside the card detail
page, so few entries have it and the valuation/P&L panel is mostly empty or
misleading. On top of that, the "Ver na LigaMagic" link on the collection
card detail opens a DIFFERENT card than the one whose price is shown.

## Scope (3 workstreams)

1. **Paid price per card** — make `acquisition_price` editable from the
   collection grid tile (quick edit), fix clearing, and make the portfolio
   summary P&L correct (foil prices, unpriced entries). See `01-paid-price.md`.
2. **Slim dashboard** — remove non-collection/non-valuation content from
   `Dashboard.tsx` (Market Summary Strip + market-empty state + the
   `fetchMarketStats` dependency that currently gates loading/error), keep
   Trending, add an investment progress block. See `02-dashboard.md`.
3. **Liga link fix** — the link must open exactly the page the Liga price was
   scraped from. Persist the fetched URL keyed like the price observation and
   serve it; safe fallback. See `03-liga-link.md`.

## Constraints

- Python 3.14 + FastAPI + SQLAlchemy; must work on PostgreSQL (Neon) AND SQLite.
  New tables are created by `Base.metadata.create_all` in `Repository.__init__`
  (`src/database/repository.py:64`) — no ALTER TABLE needed for new tables.
- Liga sweep uses `mid` price; external_id `liga_{card_id}` / `liga_{card_id}_foil`.
  Catalog source_cards use `liga_catalog_{set}_{num}`. **Do not change these.**
- No new dependencies (npm or pip).
- Every feature updates `README.md` + `docs/diagrams/F124-architecture.mmd` +
  `docs/diagrams/F124-journey.mmd`.
- Commands: `pytest tests/ --cov=src --cov-report=term-missing`,
  `cd frontend && npm test`, `cd frontend && npm run build`, `ruff check src/`.
- i18n: every new UI string goes into BOTH `frontend/src/i18n/locales/en.json`
  and `frontend/src/i18n/locales/pt-BR.json`.

## Global acceptance criteria (titles)

- AC1 — Paid price editable from each collection grid tile; saved value feeds
  `/collection/portfolio-summary` and the valuation panels.
- AC2 — Clearing the paid price persists `null` (entry leaves the investment totals).
- AC3 — Portfolio P&L uses foil prices for foil entries and does not count
  unpriced entries as a 100% loss.
- AC4 — Dashboard shows only collection/valuation content + Market Trends
  (Trending); Market Summary Strip and market-empty state are gone; dashboard
  no longer blocks on `/market/stats`.
- AC5 — Liga link on collection card detail (and catalog card detail) opens
  the same page the displayed Liga price came from; fallback link uses the
  same name source as the price fetch.
- AC6 — Backend + frontend tests green, build green, ruff clean, README and
  2 diagrams updated.
