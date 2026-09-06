# F106 — Price Alerts & Watchlist

## Summary
Users can set price alerts on any card and receive notifications when
the price crosses their target threshold (above or below).

## Tasks

### Wave 0 — Backend
- **T01**: Schema + CRUD for `price_alerts` and `alert_notifications` tables,
  plus REST API router at `/api/v1/alerts`.
- **T02**: Alert checker service (`src/services/alert_checker.py`) integrated
  into the scan hooks system so alerts are checked automatically after every
  price update.

### Wave 1 — Frontend
- **T03**: `AlertBell` component in the sidebar with badge count and dropdown.
- **T04**: `SetAlertModal` triggered from CardDetail page.
- **T05**: `/alerts` page with Active/Triggered tabs.

## Files Created/Modified

### New files
- `src/api/routers/alerts.py` — API router (6 endpoints)
- `src/services/alert_checker.py` — Alert checker service + scan hook
- `frontend/src/api/alerts.ts` — Frontend API functions
- `frontend/src/types/alerts.ts` — TypeScript types
- `frontend/src/hooks/useAlertNotifications.ts` — Polling hook
- `frontend/src/components/AlertBell.tsx` — Bell + dropdown
- `frontend/src/components/SetAlertModal.tsx` — Modal for setting alerts
- `frontend/src/pages/AlertsPage.tsx` — Full page with tabs
- `tests/api/test_alerts_router.py` — Backend tests (30 tests)
- `tests/services/test_alert_checker.py` — Service tests
- `frontend/tests/components/AlertBell.test.tsx` — Frontend tests
- `frontend/tests/components/SetAlertModal.test.tsx` — Frontend tests
- `frontend/tests/pages/AlertsPage.test.tsx` — Frontend tests

### Modified files
- `src/database/models.py` — Added `PriceAlertRow` and `AlertNotificationRow`
- `src/database/repository.py` — Imported new models
- `src/api/app.py` — Registered alerts router + alert checker hook
- `frontend/src/App.tsx` — Added `/alerts` route
- `frontend/src/components/Layout.tsx` — Added AlertBell + nav item
- `frontend/src/pages/CardDetail.tsx` — Added "Set Alert" button + modal
- `frontend/src/i18n/locales/en.json` — Added alerts i18n keys
- `frontend/src/i18n/locales/pt-BR.json` — Added alerts i18n keys

## API Endpoints
- `POST /api/v1/alerts` — Create alert
- `GET /api/v1/alerts` — List alerts (status=active|triggered|all)
- `GET /api/v1/alerts/notifications` — List notifications
- `DELETE /api/v1/alerts/{id}` — Delete alert
- `PATCH /api/v1/alerts/notifications/read` — Mark all read
