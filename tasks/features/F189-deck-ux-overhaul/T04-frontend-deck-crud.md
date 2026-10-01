# F189-T04 — Frontend: new deck modal + inline edit on DeckView

**Feature:** F191
**Wave:** 1
**Status:** planned
**Parallel:** yes (can run in parallel with T05/T06; depends on T03 for integration but can stub API)

## User Story

As a user, I want to create a new empty deck from the deck list page and edit its name and description inline on the deck view page, so I can manage deck metadata without reimporting.

## Dev Notes

### Files to MODIFY

**`frontend/src/api/decks.ts`**
- Add `createDeck()` function:
  ```typescript
  export function createDeck(
    name: string,
    description?: string,
  ): Promise<ApiResponse<DeckCreateResult>> {
    return apiPost<DeckCreateResult>("/api/v1/decks/create", {
      name,
      description: description || null,
    });
  }
  ```
  (Endpoint path depends on T03's implementation -- `/decks/create` or `/decks` with different body shape)
- Add `updateDeck()` function:
  ```typescript
  export function updateDeck(
    id: number,
    data: { name?: string; description?: string },
  ): Promise<ApiResponse<DeckDetail>> {
    return apiPut<DeckDetail>(`/api/v1/decks/${id}`, data);
  }
  ```
- Note: `apiPut` may not exist in `client.ts`. Check if `apiPatch` (line 228) exists and whether a `apiPut` helper is needed. If not, create one modeled after `apiPatch` but using `PUT` method.

**`frontend/src/types/api.ts`**
- Add `DeckCreateResult` interface:
  ```typescript
  export interface DeckCreateResult {
    deck_id: number;
    name: string;
    description: string | null;
  }
  ```

**`frontend/src/pages/DeckList.tsx`**
- Add a "New Deck" button next to the existing "Import Deck" button in the header (line 44-50 area)
- Add state: `const [showCreate, setShowCreate] = useState(false);`
- Render `<DeckCreateModal>` when `showCreate` is true
- On successful creation, navigate to `/decks/${newDeckId}` using `useNavigate()`

**`frontend/src/pages/DeckView.tsx`**
- Make deck name editable:
  - Replace static `<h1>{deck.name}</h1>` with click-to-edit pattern
  - On click: show input field with current name
  - On blur or Enter: call `updateDeck(id, { name: newName })`
  - On Escape: revert to original name
  - Show a subtle pencil icon on hover to indicate editability
- Make deck description editable:
  - Similar click-to-edit pattern for description (use textarea for multi-line)
  - If no description exists, show a "Add description" placeholder that becomes a textarea on click

### Files to CREATE

**`frontend/src/components/DeckCreateModal.tsx`**
- Modal dialog with:
  - "Create Deck" title (i18n: `decks.createTitle`)
  - Name input (required, max 200 chars)
  - Description textarea (optional)
  - Cancel + Create buttons
  - Loading state while API call is in progress
  - Error display if creation fails
- Props: `isOpen: boolean`, `onClose: () => void`, `onCreated: (deckId: number) => void`
- Style consistent with existing DeckImportModal

### i18n keys to add

**`frontend/src/i18n/locales/en.json`** (under `decks` section):
- `decks.newDeck`: "New Deck"
- `decks.createTitle`: "Create Deck"
- `decks.nameLabel`: "Deck Name"
- `decks.namePlaceholder`: "Enter deck name..."
- `decks.descriptionLabel`: "Description"
- `decks.descriptionPlaceholder`: "Optional description..."
- `decks.createButton`: "Create"
- `decks.creating`: "Creating..."
- `decks.editName`: "Edit name"
- `decks.editDescription`: "Edit description"
- `decks.addDescription`: "Add description..."

**`frontend/src/i18n/locales/pt-BR.json`** (under `decks` section):
- `decks.newDeck`: "Novo Deck"
- `decks.createTitle`: "Criar Deck"
- `decks.nameLabel`: "Nome do Deck"
- `decks.namePlaceholder`: "Digite o nome do deck..."
- `decks.descriptionLabel`: "Descricao"
- `decks.descriptionPlaceholder`: "Descricao opcional..."
- `decks.createButton`: "Criar"
- `decks.creating`: "Criando..."
- `decks.editName`: "Editar nome"
- `decks.editDescription`: "Editar descricao"
- `decks.addDescription`: "Adicionar descricao..."

### Key constraints
- `apiPut` helper may need to be created in `frontend/src/api/client.ts` if it does not exist. Model it after `apiPatch` (line 228). Do NOT add new dependencies.
- DeckCreateModal style should match DeckImportModal (same overlay, same button styles, same spacing)
- Inline edit must handle concurrent updates gracefully (optimistic UI: update local state immediately, revert on error)

### Edge cases
- Empty name submission should be prevented (disable Create button if name is empty)
- Very long names should be truncated in display but fully editable
- If the user navigates away while the create API call is in flight, no crash should occur
- Inline edit on DeckView: pressing Escape should revert changes without calling the API

## Testing

- [ ] Unit test: `DeckCreateModal` renders form fields and buttons
- [ ] Unit test: `DeckCreateModal` disables Create button when name is empty
- [ ] Unit test: `DeckCreateModal` calls onCreated with deck ID on success
- [ ] Unit test: `DeckCreateModal` shows error on API failure
- [ ] Unit test: `DeckList` renders "New Deck" button
- [ ] Unit test: `DeckList` clicking "New Deck" opens DeckCreateModal
- [ ] Unit test: `DeckView` inline name edit: click activates edit mode
- [ ] Unit test: `DeckView` inline name edit: Enter saves and exits edit mode
- [ ] Unit test: `DeckView` inline name edit: Escape reverts and exits edit mode
- [ ] Unit test: `DeckView` inline description edit works similarly
- [ ] Unit test: `createDeck` API function sends correct payload
- [ ] Unit test: `updateDeck` API function sends correct payload
- [ ] Manual: create empty deck from DeckList, verify navigation to new deck page
- [ ] Manual: edit deck name on DeckView, verify persistence after page reload
- [ ] Manual: edit deck description on DeckView, verify persistence
