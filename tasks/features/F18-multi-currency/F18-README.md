# F18 — Multi-Currency Support (BRL + USD)

## Overview

Add USD conversion support to the existing BRL-only price display. Exchange
rates are fetched daily from the BCB PTAX API, stored historically, and
applied at read time. The frontend gains a persistent currency toggle.

## Wave Plan

### Wave 0 — Data Layer (no dependencies)

| Task | Title |
|------|-------|
| F18-T01 | Exchange rate DB model + migration |
| F18-T02 | BCB PTAX API client |
| F18-T03 | Exchange rate domain models |

### Wave 1 — Backend Services (depends on Wave 0)

| Task | Title |
|------|-------|
| F18-T04 | Exchange rate repository methods |
| F18-T05 | Currency conversion service |
| F18-T06 | CLI command: update-exchange-rate |

### Wave 2 — API Layer (depends on Wave 1)

| Task | Title |
|------|-------|
| F18-T07 | Exchange rate API endpoints |
| F18-T08 | Add currency parameter to price-returning endpoints |

### Wave 3 — Frontend (depends on Wave 2)

| Task | Title |
|------|-------|
| F18-T09 | Currency context + toggle component |
| F18-T10 | Update all price-displaying pages |

### Wave 4 — Integration + Docs (depends on Wave 3)

| Task | Title |
|------|-------|
| F18-T11 | Integration tests + historical backfill script |
| F18-T12 | Diagrams, ADR, README update |

## Key Design Decisions

- BRL remains the storage currency; conversion is read-time only.
- Exchange rate = "1 USD = X BRL" (PTAX cotacaoVenda).
- Missing rates fall back to the most recent available rate.
- Frontend stores currency preference in localStorage.
- Default currency is BRL — zero breaking changes for existing behavior.

## Files Affected (Summary)

**New files:**
- `src/database/models.py` — ExchangeRateRow
- `src/domain/models.py` — ExchangeRate dataclass
- `src/providers/bcb/` — PTAX API client
- `src/services/currency.py` — conversion service
- `src/api/routers/exchange_rates.py` — new router
- `frontend/src/contexts/CurrencyContext.tsx`
- `frontend/src/components/CurrencyToggle.tsx`
- `frontend/src/utils/format.ts` — formatCurrency()

**Modified files:**
- `src/database/repository.py` — exchange rate CRUD
- `src/api/routers/cards.py` — currency param
- `src/api/routers/collection.py` — currency param
- `src/api/routers/market.py` — currency param
- `src/api/schemas/cards.py` — currency field on summaries
- `src/api/schemas/collection.py` — currency field
- `src/cli/main.py` — new command
- `frontend/src/components/Layout.tsx` — toggle in header
- `frontend/src/pages/*.tsx` — use formatCurrency
- `frontend/src/api/*.ts` — pass currency param
- `frontend/src/types/api.ts` — currency fields
