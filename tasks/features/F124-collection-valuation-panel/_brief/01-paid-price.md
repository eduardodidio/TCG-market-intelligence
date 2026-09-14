# 01 — Paid price per card (acquisition_price)

## What already exists

- Model `UserCollectionRow.acquisition_price: Numeric(12,2) | None`,
  `acquired_at: date | None` (`src/database/models.py:122-123`). **Per copy.**
- `PATCH /api/v1/collection/{entry_id}` (`src/api/routers/collection.py:689`)
  with `CollectionUpdateRequest` (`src/api/schemas/collection.py:~195-225`):
  validator rejects `<= 0` and `> 99999.99`; `model_dump(exclude_unset=True)`
  so an explicit `null` IS forwarded; `repo.update_collection_entry`
  (`repository.py:~1350-1372`) does `setattr(row, key, value)` → `null` clears.
- `GET /collection/portfolio-summary` (`collection.py:302-350`),
  `/portfolio-history`, `/export-pnl` (~L440-490), `/valuation`.
- `repo.get_portfolio_invested_total(user_id)` = `SUM(acquisition_price * quantity)`, count.
- Frontend `AcquisitionPriceInput.tsx` (price + date inline edit) used only in
  `CollectionCardDetail.tsx:413-441`; `PortfolioDashboard.tsx` on MyCollection
  (`MyCollection.tsx:692`).

## Confirmed bugs / gaps (root causes of "valor pago não alimenta o painel")

1. **List API drops the fields.** `list_collection` (`collection.py:101`,
   builder ~L167-190) constructs `CollectionCard(...)` WITHOUT
   `acquisition_price` / `acquired_at` → grid always receives `null`.
2. **Detail API drops the fields.** `_build_collection_detail`
   (`CollectionCardDetail(...)` ~L1666-1690) also omits them → after reload
   the detail page shows "empty" even though the DB has the value.
   (Only the PATCH response at ~L728 sets them.)
   Use: `acquisition_price=float(x) if x is not None else None`,
   `acquired_at=str(d) if d is not None else None`.
3. **Clearing does nothing.** `AcquisitionPriceInput.handleSavePrice` sends
   `{}` when the field is empty (backend answers 422 "No fields to update")
   yet calls `onSaved(null)`. Must send `{ acquisition_price: null }`.
   `patchCollectionEntry` type must accept `acquisition_price?: number | null`
   and `acquired_at?: string | null`.
4. **Foil P&L wrong.** `portfolio_summary` calls
   `repo.get_latest_prices_batch(card_ids)` without `foil_card_ids`, so foil
   entries are valued at the non-foil price. `list_collection` (~L140-165)
   already does it right (separate foil / non-foil maps using
   `is_foil_entry(r.extras)`) — mirror that logic.
5. **Unpriced entries count as total loss.** Entries with paid price but no
   current price add to `total_invested` but add 0 to current value.
   New semantics (PRD): `total_invested` unchanged (all entries with paid
   price); `total_pnl = total_current_value - invested_priced`, where
   `invested_priced = Σ acquisition_price × quantity` over entries that HAVE a
   current price; `total_pnl_pct` uses `invested_priced` as denominator (None
   when 0); new field `unpriced_card_count: int = 0` on `PortfolioSummary`
   schema (`src/api/schemas/collection.py`) + TS type
   (`frontend/src/types/api.ts` `PortfolioSummary`, optional `unpriced_card_count?: number`).

## Grid quick edit (new UI)

New component `frontend/src/components/PaidPriceQuickEdit.tsx`:

```ts
interface PaidPriceQuickEditProps {
  entryId: number;
  acquisitionPrice: number | null;     // per copy, BRL
  latestPrice: number | null;          // per copy, in `currency`
  currency: string;                    // current display currency
  compact?: boolean;
  onSaved: (entryId: number, price: number | null) => void;
}
```
- Display mode: "Pago: R$ 12,34" (or "Informar valor pago" link-style button
  when null). In `compact` mode: icon-only pencil button with `title`.
- When `acquisitionPrice != null && latestPrice != null && currency === "BRL"`:
  small P&L % chip (green ≥ 0, red < 0): `(latest - paid) / paid * 100`, 1 decimal.
  Hide the chip for non-BRL currency (acquisition is stored in BRL; no FX here).
- Edit mode: `<input type="number" step="0.01" min="0.01" max="99999.99">`
  + save/cancel; Enter saves, Escape cancels; empty + save → PATCH `null`.
  Client validation mirrors backend (> 0, ≤ 99999.99) with message
  `portfolio.invalidPrice` (existing key).
- **Tile is wrapped in `<Link to=/collection/:id>`** (`MyCollection.tsx:233`)
  → every click / mousedown / keydown handler inside the editor must call
  `e.preventDefault(); e.stopPropagation();` (pattern already used by the
  refresh button at `MyCollection.tsx:~128-133`). Wrap the editor root in a
  `<div onClick={stop}>`.
- Calls `patchCollectionEntry(entryId, { acquisition_price })`; on success
  `onSaved(entryId, value)`; on failure shows `inlineEdit.saveError`.
- testids: `paid-price-quick-edit-{entryId}`, `paid-price-display`,
  `paid-price-edit-btn`, `paid-price-field`, `paid-price-save`,
  `paid-price-cancel`, `paid-price-pnl`, `paid-price-error`.
- i18n (en + pt-BR): `collection.paidPrice` ("Paid"/"Pago"),
  `collection.setPaidPrice` ("Set paid price"/"Informar valor pago"),
  `collection.paidPricePerCopy` ("per copy"/"por cópia").

MyCollection integration: `CollectionCardTile` renders
`<PaidPriceQuickEdit>` under the price row; new prop
`onPaidPriceSaved`; parent updates state with the `setCards(prev => prev.map(...))`
pattern used by `handleCardRefresh` (`MyCollection.tsx:~638-650`) and
bumps a `portfolioRefreshKey` passed to `<PortfolioDashboard refreshKey={...} />`
so the valuation panel refetches. Hide the editor when `selectionMode` is on.
`PortfolioDashboard` currently fetches in a `useEffect` (L~55-65) — add an
optional `refreshKey?: number` prop to its deps.
