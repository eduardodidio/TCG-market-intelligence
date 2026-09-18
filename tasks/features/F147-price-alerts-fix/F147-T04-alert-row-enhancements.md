# F147-T04: Enhance alert rows (current price, card link, inline edit)

**Wave:** 1 (parallel with T03)
**Depends on:** T02 (PATCH endpoint for inline edit)
**Estimate:** Medium

## User Story

As a user viewing my active alerts, I want to see the card's current
price next to my target, click the card name to view its detail page,
and edit the target price inline, so that I can manage my alerts
efficiently without leaving the page.

## Problem

1. Alert rows show only the target price — no current price for context.
2. Card names are plain text, not clickable links.
3. No way to edit an alert's target price — must delete and recreate.

## Dev Notes

### 1. Show current price in active alert rows

The `AlertResponse` type does not include current_price. Two approaches:

**Option A (preferred): Add current_price to backend response.**
In `src/api/routers/alerts.py`, the `list_alerts` endpoint already joins
with `CardRow`. Extend the query to also fetch the latest price:

```python
# In the list_alerts endpoint, after fetching alerts:
# For each alert, look up latest price via liga_{card_id}
from src.database.models import PriceObservationRow

# Build a subquery for latest prices
latest_prices = {}
card_ids = [alert.card_id for alert, _ in rows]
if card_ids:
    for cid in set(card_ids):
        ext_id = f"liga_{cid}"
        price_row = session.execute(
            select(PriceObservationRow.median_price)
            .where(PriceObservationRow.external_id == ext_id)
            .order_by(PriceObservationRow.observed_at.desc())
            .limit(1)
        ).first()
        if price_row and price_row[0] is not None:
            latest_prices[cid] = float(price_row[0])
```

Add `current_price: float | None = None` to `AlertResponse` schema
(both backend Pydantic model and frontend TypeScript type).

**Option B: Fetch prices client-side.** Use the existing
`fetchPriceTrends` API for the card_ids in the alert list. This adds a
second API call but avoids backend changes.

**Go with Option A** — single request, simpler frontend.

### 2. Card name as link to card detail

In `ActiveAlertsTab` and `TriggeredAlertsTab`, wrap the card name in a
React Router `<Link>`:

```tsx
import { Link } from "react-router-dom";

<Link
  to={`/cards/${alert.card_id}`}
  className="text-sm font-medium text-white hover:text-indigo-400 truncate transition-colors"
  data-testid="alert-card-link"
>
  {alert.card_name ?? t("common.unknownCard")}
</Link>
```

### 3. Inline edit for target price

Add an inline edit mode on the target price in active alert rows:

```
State per row: editingId: number | null

Display mode:
  "Below R$ 15.00" [pencil icon]

Edit mode (click pencil):
  "Below R$" [input field: 15.00] [check button] [x button]

On confirm: call updateAlert(alertId, { target_price: newPrice })
On success: refetch alerts
On cancel: revert to display mode
```

Use the `updateAlert` function from T02.

Consider extracting an `InlineEditPrice` component or reusing the
existing `InlineEditField` component if its API fits (it was created
in F98).

### Changes summary

#### Backend
- `src/api/routers/alerts.py`:
  - Add `current_price: float | None = None` to `AlertResponse`
  - In `list_alerts`, query latest prices for alert card_ids
- `tests/api/test_alerts_router.py`: verify current_price in response

#### Frontend
- `frontend/src/types/alerts.ts`: add `current_price` to `AlertResponse`
- `frontend/src/pages/AlertsPage.tsx`:
  - Import `Link` from react-router-dom
  - Wrap card names in `<Link to={/cards/${card_id}}>`
  - Add inline edit state and UI for target price
  - Import and call `updateAlert` from api/alerts
  - Show current price with visual indicator (green if below target for
    "below" alerts, red if above target for "above" alerts)
- `frontend/src/locales/en/translation.json` + pt-BR:
  - `alerts.currentPrice`: "Current: R$ {{price}}" / "Atual: R$ {{price}}"
  - `alerts.editTargetPrice`: "Edit target price" / "Editar preco alvo"
  - `alerts.priceUpdated`: "Target price updated" / "Preco alvo atualizado"

### Current price display format

Show current price on a second line below the direction + target:

```
Below R$ 15.00                    [edit] [delete]
Current: R$ 18.50 (23% above)
Created: 2026-09-15
```

Color coding:
- For "below" alerts: green if current > target (not yet triggered),
  yellow if within 10%, red if current <= target (should have triggered)
- For "above" alerts: inverse logic

## Testing

### Backend tests
- `list_alerts` response includes `current_price` field.
- `current_price` is null when no price observation exists.
- `current_price` reflects the latest observation.

### Frontend tests (`frontend/tests/pages/AlertsPage.test.tsx`)
- Card name renders as a link to `/cards/:id`.
- Current price is displayed when available.
- Clicking pencil icon enters edit mode.
- Submitting new price calls `updateAlert`.
- Cancel reverts to display mode.
- Successful update refetches the alert list.

## Acceptance Criteria
- [ ] Active alert rows show current price alongside target price
- [ ] Card names are clickable links to `/cards/:id`
- [ ] Pencil icon on active alerts enables inline target price editing
- [ ] Inline edit calls PATCH endpoint and refreshes list on success
- [ ] Current price has color coding relative to target
- [ ] Triggered alert rows also show card name as link
- [ ] Backend and frontend tests cover new behavior
- [ ] i18n keys for en and pt-BR
