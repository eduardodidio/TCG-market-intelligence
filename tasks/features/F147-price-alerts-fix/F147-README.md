# F147 — Price Alerts Fix (Broken Functionality)

**Status:** planned
**Branch:** homol
**Created:** 2026-09-18

## Problem Statement

The price alerts feature (F106) is technically complete but functionally
broken from the user's perspective. Multiple issues prevent effective use:

1. **Alerts never fire from daily-scan:** The CLI `liga-sweep` command
   (used by `daily-scan.bat`) calls `run_liga_sweep()` which does NOT
   accept or invoke an `on_complete` callback. Scan hooks (including
   `alert_checker`) only fire from API/scheduler paths, never from the
   CLI path that actually runs daily. This means alerts are effectively
   dead code in the production workflow.

2. **No way to create alerts from AlertsPage:** Users must navigate to a
   specific card detail page and find the SetAlertModal there. The
   AlertsPage itself has no "Create Alert" button and no card search.

3. **No current price context:** Active alerts show only the target price,
   not the card's current price. Users cannot assess how close an alert
   is to triggering.

4. **Alert rows are dead-end UI:** Card names in alert rows are plain text
   with no link to the card detail page.

5. **No edit capability:** Users must delete and recreate an alert to
   change the target price. No PATCH/PUT endpoint exists.

6. **AlertBell is in the sidebar** (confirmed working) and links to
   /alerts via "View All" in the dropdown (confirmed working).

## Root Cause Analysis

- `run_liga_sweep()` in `src/collectors/liga_sweep.py` does not accept an
  `on_complete` parameter. The API scan endpoints pass
  `on_complete=default_registry.notify` to `run_liga_scan`, but the CLI
  `liga-sweep` command calls `run_liga_sweep()` which has no hook support.
- `daily-scan.bat` runs `liga-sweep` via CLI, so hooks never fire.
- The SetAlertModal requires `cardId` and `cardName` props, making it
  impossible to use without a pre-selected card.

## Waves

### Wave 0 — Backend fixes (sequential)
- **T01:** Add `on_complete` callback to `run_liga_sweep()` + wire CLI
- **T02:** Add PATCH endpoint for updating alert target_price

### Wave 1 — Frontend improvements (parallel)
- **T03:** Add "Create Alert" flow on AlertsPage (card search + modal)
- **T04:** Enhance alert rows (current price, card link, inline edit)

## Scope
- **IN:** Backend hook wiring, PATCH endpoint, AlertsPage UX, card search
  in modal, alert row enhancements
- **OUT:** New alert types, push notifications, email alerts, new alert
  conditions (percent change, volume)

## Files Likely Touched

### Backend
- `src/collectors/liga_sweep.py` — add `on_complete` param
- `src/cli/main.py` — pass `on_complete` in liga-sweep + catalog-scan
- `src/api/routers/alerts.py` — add PATCH endpoint
- `tests/` — new tests for hook wiring and PATCH

### Frontend
- `frontend/src/pages/AlertsPage.tsx` — create button, card search, row enhancements
- `frontend/src/components/SetAlertModal.tsx` — optional card search mode
- `frontend/src/api/alerts.ts` — add updateAlert function
- `frontend/src/types/alerts.ts` — add UpdateAlertRequest type
- `frontend/src/locales/` — new i18n keys
- `frontend/tests/` — new tests
