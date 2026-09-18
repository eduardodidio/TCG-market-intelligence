# F147-T03: Add "Create Alert" flow on AlertsPage with card search

**Wave:** 1 (parallel with T04)
**Depends on:** T02 (PATCH endpoint must exist for full modal reuse)
**Estimate:** Medium

## User Story

As a user on the Alerts page, I want to create a new price alert by
searching for a card by name and setting a target price, so that I do not
need to navigate to a specific card detail page first.

## Problem

The AlertsPage has no "Create Alert" button. The SetAlertModal requires
`cardId` and `cardName` props, meaning it can only be opened from a
context where a card is already selected (card detail page). There is no
card search built into the alert creation flow.

## Dev Notes

### Approach: CardSearchAlertModal (new component)

Create a new wrapper component that combines card search with the
existing SetAlertModal. Two-step flow:

1. **Step 1 — Search:** Text input with debounced search (300ms). Uses
   the existing `GET /api/v1/cards?q=<term>` endpoint which returns
   `CardSummary[]` (id, name_en, set_code, latest_price). Show results
   in a scrollable list with card name, set, and current price.

2. **Step 2 — Set Alert:** Once user selects a card, render the existing
   SetAlertModal inline (or pass cardId/cardName to it).

### File: `frontend/src/components/CardSearchAlertModal.tsx`

```
Props: { onClose: () => void; onAlertCreated: () => void }

State:
  - step: "search" | "configure"
  - searchTerm: string
  - selectedCard: { id: number; name: string } | null
  - searchResults: CardSummary[]
  - searching: boolean

Step 1 UI:
  - Modal overlay (same style as SetAlertModal)
  - Search input with magnifying glass icon
  - Results list: card name | set code | R$ current_price
  - Click result -> setSelectedCard, move to step 2
  - "Back" button in step 2 to return to search

Step 2 UI:
  - Reuse SetAlertModal's form (direction toggle + price input + submit)
  - OR simply render <SetAlertModal cardId={...} cardName={...} />
    with a "Back to search" link
```

### Alternative: Extend SetAlertModal with optional card search

Instead of a new component, make `cardId` and `cardName` optional in
SetAlertModal. When not provided, show a search step first. This is
cleaner but requires more changes to the existing component.

**Recommended:** New wrapper component. Keeps SetAlertModal's existing
contract intact, avoids regression risk on card detail pages.

### Changes to `frontend/src/pages/AlertsPage.tsx`

1. Add state: `const [showCreateModal, setShowCreateModal] = useState(false);`
2. Add button next to the page title:
   ```tsx
   <button
     onClick={() => setShowCreateModal(true)}
     className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-md"
     data-testid="create-alert-button"
   >
     {t("alerts.createAlert")}
   </button>
   ```
3. Render modal conditionally:
   ```tsx
   {showCreateModal && (
     <CardSearchAlertModal
       onClose={() => setShowCreateModal(false)}
       onAlertCreated={() => { setShowCreateModal(false); refetchActive(); }}
     />
   )}
   ```

### Changes to `frontend/src/api/cards.ts`

The existing `fetchCards(params)` function already supports `?q=<term>`
for search. No new API function needed.

### i18n keys needed (en + pt-BR)

- `alerts.createAlert` — "Create Alert" / "Criar Alerta"
- `alerts.searchCard` — "Search for a card..." / "Buscar carta..."
- `alerts.selectCard` — "Select a card to set an alert" / "Selecione uma carta para criar alerta"
- `alerts.noResults` — "No cards found" / "Nenhuma carta encontrada"
- `alerts.backToSearch` — "Back to search" / "Voltar para busca"

## Testing

### Component tests (`frontend/tests/components/CardSearchAlertModal.test.tsx`)
- Renders search input on open.
- Typing in search input triggers API call (debounced).
- Clicking a search result shows the alert configuration form.
- "Back" button returns to search step.
- Creating an alert calls onAlertCreated callback.
- Escape key closes modal.

### Page tests (`frontend/tests/pages/AlertsPage.test.tsx`)
- "Create Alert" button is visible.
- Clicking it opens CardSearchAlertModal.
- After alert creation, active alerts list refetches.

## Acceptance Criteria
- [ ] "Create Alert" button visible on AlertsPage header
- [ ] Clicking it opens a modal with card search
- [ ] Card search uses existing `/api/v1/cards?q=` endpoint
- [ ] Search results show card name, set, current price
- [ ] Selecting a card shows direction + target price form
- [ ] After creating alert, modal closes and alert list refreshes
- [ ] i18n keys for en and pt-BR
- [ ] Component and page tests pass
