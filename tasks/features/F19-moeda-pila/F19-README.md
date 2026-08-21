# F19 -- Moeda "Pila" (RS)

**Status:** planned
**Owner:** @eduardodidio
**PRD:** [`docs/prd/F19-moeda-pila.md`](../../../docs/prd/F19-moeda-pila.md)
**Prerequisites:** F18 (multi-currency infra), F22 (authentication/login)

## Goal

Add "Pila" as a custom regional currency (1:1 with BRL) with extenso formatting
and the Rio Grande do Sul flag icon, leveraging the F18 multi-currency infrastructure
and F22 user preferences.

## Architecture Impact

- `src/domain/models.py` -- new `PilaCurrency` constant or seed data reference
- `src/currency/` -- new `pila_formatter.py` with extenso formatting logic (or extend F18 formatter)
- `src/database/` -- seed migration to insert PILA currency row
- `src/api/schemas/` -- currency preference field on user settings (extends F22)
- `frontend/src/utils/format.ts` -- new `formatPila()` function
- `frontend/src/utils/currency.ts` -- currency-aware dispatcher that delegates to formatBRL or formatPila
- `frontend/src/assets/` -- RS flag SVG asset
- `frontend/src/components/CurrencyIndicator.tsx` -- updated to show RS flag for PILA
- All price display points across pages -- updated to use currency-aware formatter

## Wave Manifest

- **Wave 0**: F19-T01, F19-T02        (backend formatter + seed data, parallel)
- **Wave 1**: F19-T03, F19-T04        (frontend formatter + RS flag asset, parallel)
- **Wave 2**: F19-T05                 (integrate formatter into all price display points)
- **Wave 3**: F19-T06                 (user preference wiring via F22 auth)
- **Wave 4**: F19-T07                 (diagrams + documentation)

## Global Acceptance Criteria

- [ ] "PILA" currency registered in multi-currency system with fixed 1:1 rate
- [ ] Backend formatter produces correct extenso output for all edge cases
- [ ] Frontend formatter produces correct extenso output for all edge cases
- [ ] RS flag icon displays next to Pila amounts in all price contexts
- [ ] Selecting Pila as preferred currency switches all price displays to extenso format
- [ ] Switching back to BRL restores standard R$ formatting
- [ ] Singular/plural rules correct: pila/pilas, centavo/centavos
- [ ] Null/undefined values display as "--"
- [ ] All existing tests pass (857+ backend, 304+ frontend)
- [ ] New tests added for formatter (coverage >= 90%)
- [ ] README.md updated with F19 delivery notes

## Diagrams

- `docs/diagrams/F19-architecture.mmd` -- currency formatting data flow
- `docs/diagrams/F19-journey.mmd` -- user journey for selecting Pila currency
