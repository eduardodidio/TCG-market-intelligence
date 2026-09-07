# F105 — Portfolio & Investment Tracking

## Overview
Track acquisition costs, calculate P&L per card and across the portfolio,
visualize portfolio value over time, and export data for tax purposes.

## Tasks

### Wave 0 (Schema + Backend)
- **T01**: Added `acquisition_price` (NUMERIC(12,2), nullable) and `acquired_at` (DATE, nullable) to `user_collection` table. Migration via `_ensure_columns()` in repository.py.
- **T02**: Three new API endpoints:
  - `GET /api/v1/collection/portfolio-summary` — invested, current value, P&L
  - `GET /api/v1/collection/portfolio-history?days=90` — time series from snapshots
  - `GET /api/v1/collection/export-pnl` — CSV download for tax/IR
  - Extended `PATCH /api/v1/collection/{id}` to accept `acquisition_price` and `acquired_at`

### Wave 1 (Frontend)
- **T03**: `AcquisitionPriceInput` — inline editable price + date picker in CollectionCardDetail
- **T04**: `PnlBadge` — shows per-card unrealized P&L (green/red)
- **T05**: `PortfolioDashboard` — KPI panel + Recharts line chart + export button on MyCollection

### Wave 2 (Export)
- **T06**: CSV export via `GET /api/v1/collection/export-pnl` + "Export P&L" button in PortfolioDashboard

## Files Changed
- `src/database/models.py` — UserCollectionRow: acquisition_price, acquired_at
- `src/database/repository.py` — migration + new methods + editable fields
- `src/api/schemas/collection.py` — new schemas (PortfolioSummary, PortfolioHistoryPoint, PnlExportRow), extended CollectionUpdateRequest and CollectionCard
- `src/api/routers/collection.py` — 3 new endpoints + extended PATCH
- `frontend/src/types/api.ts` — PortfolioSummary, PortfolioHistoryPoint, updated CollectionCard
- `frontend/src/api/collection.ts` — fetchPortfolioSummary, fetchPortfolioHistory, exportPnlCsv
- `frontend/src/components/PnlBadge.tsx` — new
- `frontend/src/components/AcquisitionPriceInput.tsx` — new
- `frontend/src/components/PortfolioDashboard.tsx` — new
- `frontend/src/pages/CollectionCardDetail.tsx` — integrated AcquisitionPriceInput + PnlBadge
- `frontend/src/pages/MyCollection.tsx` — integrated PortfolioDashboard
- `frontend/src/i18n/locales/en.json` — portfolio.* keys
- `frontend/src/i18n/locales/pt-BR.json` — portfolio.* keys

## Tests
- `tests/api/test_collection_portfolio.py` — 12 backend tests
- `frontend/tests/components/PnlBadge.test.tsx` — 3 tests
- `frontend/tests/components/PortfolioDashboard.test.tsx` — 5 tests
- `frontend/tests/components/AcquisitionPriceInput.test.tsx` — 5 tests
