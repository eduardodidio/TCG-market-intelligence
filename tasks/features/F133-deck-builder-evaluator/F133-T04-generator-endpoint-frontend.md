# F133-T04: Generator Endpoint + Frontend Wizard

**Wave:** 1
**Status:** planned
**Depends on:** F133-T02

## User Story

As a user, I want a step-by-step wizard to generate a deck by choosing
format, commander (optional), archetype, colors, and budget so that I
can quickly create a new deck without manually picking every card.

## Description

Create the API endpoint `POST /api/v1/decks/generate` and a multi-step
wizard page at `/decks/build` in the frontend.

## Backend

### Endpoint: `POST /api/v1/decks/generate`

Add to `src/api/routers/decks.py`.

Request body (`DeckGenerateRequest`):
```python
class DeckGenerateRequest(BaseModel):
    format_name: str  # "commander", "standard", "modern", etc.
    commander_card_id: int | None = None
    colors: list[str] = []  # ["W", "U", "B", "R", "G"]
    archetype: str | None = None  # "aggro", "control", etc.
    budget_limit: float | None = None  # BRL
    prioritize_owned: bool = False
    deck_name: str | None = None  # auto-generated if None
    exclude_card_ids: list[int] = []
```

Response (`DeckGenerateResponse`):
```python
class DeckGenerateResponse(BaseModel):
    deck_id: int
    name: str
    format_name: str
    archetype: str | None
    colors: list[str]
    total_cards: int
    land_count: int
    nonland_count: int
    total_value: float | None
    warnings: list[str]
    cards: list[GeneratedCardSchema]

class GeneratedCardSchema(BaseModel):
    card_id: int
    name_en: str
    set_code: str | None
    collector_number: str | None
    quantity: int
    mana_cost: str | None
    type_line: str | None
    rarity: str | None
    image_uri: str | None
    price: float | None
    is_owned: bool
```

Logic:
1. Validate format_name is recognized
2. If commander_card_id provided, verify card exists and is a
   legendary creature (type_line contains "Legendary" and "Creature")
3. Build DeckBuildParams from request
4. Call `generate_deck(repo, params)`
5. Auto-save the generated deck via `repo.create_deck()` +
   `repo.add_deck_cards()`
6. Return the generated deck with card details

### Commander Search Helper

Add `GET /api/v1/decks/commanders` endpoint:
- Query params: `q` (search term), `colors` (comma-separated),
  `limit` (default 20)
- Searches CardRow where type_line LIKE "%Legendary%" AND type_line
  LIKE "%Creature%" AND name_en ILIKE "%{q}%"
- Filters by color_identity subset if colors provided
- Returns list of {card_id, name_en, color_identity, mana_cost,
  type_line, image_uri, set_code, collector_number}

## Frontend

### API Client

Add to `frontend/src/api/decks.ts`:

```ts
export async function generateDeck(params: DeckGenerateParams):
  Promise<ApiResponse<DeckGenerateResult>> { ... }

export async function searchCommanders(query: string, colors?: string[]):
  Promise<ApiResponse<CommanderSearchResult[]>> { ... }
```

### Type Definitions

Add to `frontend/src/types/api.ts`:
- `DeckGenerateParams`
- `DeckGenerateResult`
- `CommanderSearchResult`

### Page: `DeckBuildWizard` (`/decks/build`)

File: `frontend/src/pages/DeckBuildWizard.tsx`

Multi-step wizard with progress indicator at the top:

**Step 1 — Format Selection**
- Radio buttons for: Commander, Standard, Modern, Legacy, Pauper,
  Casual
- Brief description of each (card count, special rules)
- "Next" button

**Step 2 — Commander / Colors** (conditional)
- If Commander format: search field for commander name, debounced
  search calls `/api/v1/decks/commanders`, shows card image previews
  as selectable grid. Selecting a commander auto-sets colors.
- If other format: color selector — 5 toggleable MTG color buttons
  (W, U, B, R, G) with icons/symbols. At least 1 must be selected.
- "Back" and "Next" buttons

**Step 3 — Archetype & Budget**
- Archetype selector: radio cards for Aggro, Control, Midrange,
  Combo, Tempo (each with 1-line description of playstyle)
- Budget limit: optional number input in BRL, with presets
  (R$100, R$500, R$1000, No limit)
- Checkbox: "Prioritize cards I own"
- "Back" and "Generate" buttons

**Step 4 — Review & Save**
- Shows generated deck in a card grid (reuse DeckCardTile or
  similar)
- Summary stats: total cards, lands, avg CMC, total value
- Warnings displayed as alert banners
- Deck name input (pre-filled with auto-generated name like
  "WU Control — 2026-09-17")
- "Save Deck" button -> saves and navigates to `/decks/{id}`
- "Regenerate" button -> calls generate again with same params
- "Back" button to modify params

### Routing

Add route in App.tsx: `<Route path="/decks/build" element={<DeckBuildWizard />} />`

Ensure this route is defined BEFORE `/decks/:id` to avoid conflict.

## Dev Notes

- The wizard state lives in component state (not URL params) since
  it's a multi-step form. Consider `useReducer` for clarity.
- Commander search should be debounced (300ms) to avoid excessive
  API calls.
- The generate endpoint saves the deck immediately. The "Review"
  step shows the saved deck. "Regenerate" deletes the old one and
  creates a new one.
- Auto-generated deck name format: `"{colors} {archetype} — {date}"`
  e.g. "WU Control — 2026-09-17".
- Credit cost: deck generation is free (no credit charge). It uses
  catalog data only, no external scraping.
- If commander_card_id is provided but the card is not legendary or
  not a creature, return 400 with a clear error message.

## Testing

### Backend (15+ tests)
- Test generate endpoint with valid commander params -> 200, 100 cards
- Test generate endpoint with standard format -> 60 cards
- Test generate endpoint with invalid format -> 400
- Test generate endpoint with invalid commander (not legendary) -> 400
- Test generate endpoint with budget_limit -> total_value <= limit
- Test commander search with query -> returns legendary creatures
- Test commander search with color filter -> respects color identity
- Test commander search with empty query -> returns top 20
- Test deck is saved and retrievable via GET /decks/{id}
- Test prioritize_owned flag (requires seeded collection)
- Test exclude_card_ids are not in result

### Frontend (12+ tests)
- Test wizard renders Step 1 by default
- Test format selection enables Next button
- Test Step 2 shows commander search for commander format
- Test Step 2 shows color picker for other formats
- Test Step 3 shows archetype options and budget input
- Test Generate button calls API
- Test Step 4 shows generated deck cards
- Test Save button navigates to deck page
- Test Regenerate button re-calls API
- Test Back button navigates between steps
- Test loading state during generation
- Test error state shows warning
