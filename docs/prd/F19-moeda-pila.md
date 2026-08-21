# PRD: F19 - Moeda "Pila" (RS)

**Feature ID:** F19
**Status:** draft
**Owner:** @eduardodidio
**Date:** 2026-08-21
**Prerequisites:** F18 (multi-currency infra), F22 (authentication/login)

## Problem

The application currently displays all prices exclusively in BRL (Brazilian Real).
The user wants a novelty/regional currency called "Pila" -- the informal name for
money in Rio Grande do Sul -- displayed with a unique extenso format
(e.g., "230 pilas e 21 centavos") and the RS state flag as its symbol. This is a
1:1 mapping to BRL, so it carries no exchange rate complexity, but it requires a
custom formatter that writes values out in words rather than using a currency symbol.

The user's preferred currency (including Pila) will be stored as a user preference,
which depends on the authentication system from F22.

## Goal

Allow the user to select "Pila" as their display currency, causing all price values
throughout the application to render in the extenso format with the RS flag icon,
while maintaining BRL as the underlying storage currency.

## Scope

### In scope

- Register "PILA" as a custom currency in the F18 multi-currency system
- Fixed 1:1 exchange rate to BRL (never changes, no rate fetching)
- Custom extenso formatter: `R$ 230,21` becomes `230 pilas e 21 centavos`
- Edge cases in formatter: singular "pila"/"centavo", zero centavos, zero value
- RS state flag icon (SVG or emoji) for currency indicator in UI
- Frontend currency formatting hook/utility that dispatches to the Pila formatter
  when the active currency is PILA
- User preference persistence for default currency (requires F22 auth infra)
- All existing price display points updated to use the currency-aware formatter
- Backend: Pila currency seed data, formatter utility
- Frontend: Pila formatter, RS flag asset, currency selector integration

### Out of scope

- Any actual exchange rate conversion (Pila is always 1:1 with BRL)
- Other custom/novelty currencies
- Server-side price conversion (prices are stored in BRL, formatting is display-only)
- Multi-language support for the extenso format (Portuguese only)
- F18 multi-currency infra itself (assumed to exist)
- F22 authentication itself (assumed to exist)

## User Flows

1. User logs in (F22) and navigates to Settings/Preferences
2. User selects "Pila (RS)" from the currency dropdown (which also shows BRL, USD, etc. from F18)
3. All price displays across the app switch to extenso format with RS flag
4. Example transformations:
   - Collection total value: `R$ 4.521,30` -> `[RS flag] 4.521 pilas e 30 centavos`
   - Card price: `R$ 0,50` -> `[RS flag] 0 pilas e 50 centavos`
   - Card price: `R$ 1,00` -> `[RS flag] 1 pila`
   - Card price: `R$ 1,01` -> `[RS flag] 1 pila e 1 centavo`
   - Null/missing: `--`

See `docs/diagrams/F19-journey.mmd` for the full user flow.

## Technical Notes

### Formatter Rules

| Value (BRL) | Pila Display |
|-------------|--------------|
| 0.00 | 0 pilas |
| 0.01 | 0 pilas e 1 centavo |
| 0.50 | 0 pilas e 50 centavos |
| 1.00 | 1 pila |
| 1.01 | 1 pila e 1 centavo |
| 1.50 | 1 pila e 50 centavos |
| 230.21 | 230 pilas e 21 centavos |
| 1000.00 | 1.000 pilas |
| 1234567.89 | 1.234.567 pilas e 89 centavos |

Rules:
- Integer part uses pt-BR thousands separator (`.`)
- "pila" (singular) when integer part is exactly 1; "pilas" otherwise
- "centavo" (singular) when fractional part is exactly 1; "centavos" otherwise
- Omit "e N centavo(s)" when fractional part is 0
- Null/undefined values display as `--`

### Currency Registration

The F18 multi-currency system is assumed to provide:
- A `Currency` model/table with code, name, symbol, exchange_rate fields
- A way to register new currencies
- A frontend currency context/selector

F19 adds a PILA row:
- code: `PILA`
- name: `Pila (Rio Grande do Sul)`
- symbol: RS flag icon
- rate_to_brl: `1.0` (fixed, never updated)
- formatter: custom extenso (not the standard `Intl.NumberFormat`)

## Success Metrics

| Metric | Target |
|--------|--------|
| Formatter accuracy | 100% of edge cases in the rules table produce correct output |
| UI consistency | All price display points use currency-aware formatter |
| Test coverage | >= 90% for new code |
| No regressions | All existing tests pass |

## Open Questions

- Should the thousands separator in the integer part follow pt-BR locale (`.`) or
  be omitted for readability? Decision: use pt-BR locale (`.`) for consistency.
- Should there be an abbreviated format for compact displays (e.g., `230,21 P`)?
  Decision: deferred, not in scope for F19.
