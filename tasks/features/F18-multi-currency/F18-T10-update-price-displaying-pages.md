# F18-T10: Update All Price-Displaying Pages

- **Wave:** 3
- **Status:** done
- **Depends on:** F18-T09
- **Description:**
  Update every frontend page and component that displays prices to:

  1. Use `useCurrency()` to get the selected currency.
  2. Pass `?currency=<selected>` on all API calls that return prices.
  3. Replace `formatBRL()` calls with `formatCurrency(value, currency)`.
  4. Update the PriceChart Y-axis label to show the active currency.

  Pages and components to update:

  - **Dashboard.tsx** — collection value KPI, market avg price KPI.
  - **MyCollection.tsx** — card tiles `latest_price`, summary `total_value`.
  - **CollectionCardDetail.tsx** — `latest_price` display, price history.
  - **Cards.tsx** — card list `latest_price`.
  - **CardDetail.tsx** — `latest_price`.
  - **MarketMovers.tsx** — `price_start`, `price_end` in mover entries.
  - **MoversPreview.tsx** — same as MarketMovers.
  - **MoversTable.tsx** — price columns.
  - **CardTile.tsx** — price display.
  - **PriceChart.tsx** — Y-axis label, tooltip format.
  - **KpiCard.tsx** — no change needed (receives formatted string).

  API client updates:

  - **`frontend/src/api/collection.ts`** — add currency param.
  - **`frontend/src/api/cards.ts`** — add currency param.
  - **`frontend/src/api/market.ts`** — add currency param.

- **Acceptance Criteria:**
  - [ ] All price displays use `formatCurrency` with selected currency
  - [ ] All API calls pass `?currency=<selected>`
  - [ ] Switching currency updates all visible prices without page reload
  - [ ] PriceChart Y-axis shows "R$" or "$" based on currency
  - [ ] No hardcoded `formatBRL` calls remain (except the alias definition)
  - [ ] Existing frontend tests updated to pass with new currency parameter
  - [ ] New tests: verify currency toggle changes displayed values
  - [ ] Visual regression: BRL mode looks identical to current behavior

- **Files to touch:**
  - `frontend/src/pages/Dashboard.tsx`
  - `frontend/src/pages/MyCollection.tsx`
  - `frontend/src/pages/CollectionCardDetail.tsx`
  - `frontend/src/pages/Cards.tsx`
  - `frontend/src/pages/CardDetail.tsx`
  - `frontend/src/pages/MarketMovers.tsx`
  - `frontend/src/components/MoversPreview.tsx`
  - `frontend/src/components/MoversTable.tsx`
  - `frontend/src/components/CardTile.tsx`
  - `frontend/src/components/PriceChart.tsx`
  - `frontend/src/api/collection.ts`
  - `frontend/src/api/cards.ts`
  - `frontend/src/api/market.ts`
  - `frontend/tests/pages/*.test.tsx` (update)
