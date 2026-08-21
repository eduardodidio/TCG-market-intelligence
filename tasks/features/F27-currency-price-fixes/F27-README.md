# F27 — Currency & Price Fixes

**Status:** planned
**Created:** 2026-08-21
**Priority:** high

## Summary

Fix currency system: ensure values actually convert (not just symbol swap),
add country flags for BRL/USD, show exchange rate when USD selected, make
PILA uppercase, and diagnose/fix missing card prices.

## Problems

1. Currency toggle changes symbol but values don't convert properly
   - Root cause: if no exchange rate is seeded, `converter.convert()` returns
     `None` and the `or g[3]` fallback shows BRL value with USD symbol
   - Also: `formatCurrency()` gets the already-converted value but some pages
     may not pass `currency` param to API
2. No exchange rate displayed — users don't know the conversion basis
3. BRL shows "R$" text, USD shows "$" text — no country flags
4. PILA label is "Pila" (mixed case) instead of "PILA" (uppercase)
5. Many cards show no price in market movers and explore cards

## Tasks

| Task | Description | Wave |
|------|------------|------|
| T01 | Country flags for BRL/USD + PILA uppercase | 1 |
| T02 | Exchange rate banner when USD selected | 1 |
| T03 | Audit & fix currency param passing in all frontend API calls | 1 |
| T04 | Fix converter fallback: handle None rate gracefully | 1 |
| T05 | Diagnose & fix missing card prices | 2 |

## Waves

- **Wave 1** (parallel): T01, T02, T03, T04 — independent UI & logic fixes
- **Wave 2**: T05 — requires Wave 1 to verify price display works correctly

## Dependencies

- Exchange rates must be seeded in DB (`seed-exchange-rate` CLI command)
- F18 (multi-currency) infrastructure already in place
