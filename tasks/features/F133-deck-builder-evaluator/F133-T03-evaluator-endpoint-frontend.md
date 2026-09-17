# F133-T03: Evaluator Endpoint + Frontend Panel

**Wave:** 1
**Status:** planned
**Depends on:** F133-T01

## User Story

As a user, when viewing one of my decks, I want to see a visual
evaluation panel showing mana curve chart, type distribution pie,
color breakdown, legality status, and budget analysis so that I can
quickly identify strengths and weaknesses of my deck.

## Description

Create the API endpoint `GET /api/v1/decks/{deck_id}/evaluate` and
a new frontend component `DeckEvaluationPanel` integrated into
DeckView.tsx.

## Backend

### Endpoint: `GET /api/v1/decks/{deck_id}/evaluate`

Add to `src/api/routers/decks.py`.

Query params:
- `format`: str (optional) — format to check legality against
  (default: "commander")
- `currency`: str (default: "BRL")

Logic:
1. Verify deck exists and belongs to authenticated user
2. Fetch deck cards via `repo.get_deck_cards(deck_id)`
3. For each card with a `card_id`, JOIN with CardRow to get
   `mana_cost`, `type_line`, `color_identity`, `rarity`
4. Batch-fetch prices via `repo.get_latest_prices_batch(card_ids)`
5. Batch-fetch legalities via
   `repo.get_legalities_for_cards_batch(card_ids)`
6. Assemble enriched card list and call
   `evaluate_deck(cards, prices, legalities, format)`
7. Return `DeckEvaluationResponse`

### Response Schema (`DeckEvaluationResponse`)

```python
class ManaCurvePoint(BaseModel):
    cmc: int
    count: int

class TypeDistEntry(BaseModel):
    type_name: str
    count: int

class ColorDistEntry(BaseModel):
    color: str
    pip_count: int

class IllegalCard(BaseModel):
    name_en: str
    status: str

class LegalityResult(BaseModel):
    format: str
    is_legal: bool
    illegal_cards: list[IllegalCard]
    singleton_violations: list[str]
    card_count_valid: bool

class BudgetEntry(BaseModel):
    name_en: str
    price: float
    quantity: int

class BudgetAnalysis(BaseModel):
    total_value: float
    most_expensive: list[BudgetEntry]
    price_tiers: dict[str, int]

class DeckEvaluationResponse(BaseModel):
    deck_id: int
    mana_curve: list[ManaCurvePoint]
    type_distribution: list[TypeDistEntry]
    color_distribution: list[ColorDistEntry]
    land_count: int
    nonland_count: int
    total_cards: int
    avg_cmc: float
    color_identity: list[str]
    legality: LegalityResult | None
    budget: BudgetAnalysis | None
    suggestions: list[str]
```

## Frontend

### API Client

Add to `frontend/src/api/decks.ts`:

```ts
export async function fetchDeckEvaluation(
  deckId: number,
  format?: string,
): Promise<ApiResponse<DeckEvaluation>> { ... }
```

### Type Definition

Add `DeckEvaluation` to `frontend/src/types/api.ts` matching the
response schema above.

### Component: `DeckEvaluationPanel`

File: `frontend/src/components/DeckEvaluationPanel.tsx`

Props: `{ deckId: number }`

Sections (each in a card/panel):

1. **Mana Curve** — Recharts `BarChart` with CMC on X-axis, count on
   Y-axis. Blue bars. Label "Avg CMC: X.X" below chart.

2. **Type Distribution** — Recharts `PieChart` with segments for each
   card type. Use distinct colors per type (green=Creature,
   blue=Instant, red=Sorcery, yellow=Enchantment, gray=Artifact,
   brown=Land, purple=Planeswalker). Show count labels.

3. **Color Distribution** — horizontal bar or pie showing color pip
   counts. Use MTG colors (W=gold, U=blue, B=gray/black, R=red,
   G=green, C=silver).

4. **Legality** — if format specified: green checkmark + "Legal in
   Commander" or red X + list of illegal cards and violations.

5. **Budget** — total value, top 5 most expensive cards with prices,
   price tier breakdown as small bar chart or stat row.

6. **Suggestions** — bulleted list of suggestion strings (populated
   by T05, empty initially).

### Integration into DeckView

Add a tab or collapsible section below the value panel in DeckView.tsx.
Two views: "Cards" (existing grid) and "Evaluation" (new panel).
Toggle between them with tab buttons.

### Styling

- Use existing dark theme styles (bg-slate-800, text-white, etc.)
- Responsive: stack panels vertically on mobile, 2-col grid on desktop
- Loading skeleton while evaluation fetches

## Dev Notes

- Evaluation is computed on-demand (not cached), since it depends on
  current prices and legality data which change daily.
- The endpoint reuses existing repository methods: get_deck_cards,
  get_latest_prices_batch, get_legalities_for_cards_batch. No new
  repo methods needed.
- For cards without a card_id link (unresolved imports), skip them in
  the evaluation but include a warning in suggestions.
- Charts use Recharts (already a project dependency).
- Format selector in the frontend: a dropdown defaulting to
  "commander" with options for standard, modern, legacy, pauper.

## Testing

### Backend (12+ tests)
- Test endpoint returns 404 for nonexistent deck
- Test endpoint returns 404 for other user's deck
- Test successful evaluation: verify mana_curve is list of
  ManaCurvePoint, type_distribution sums correctly
- Test legality_check with a deck containing a banned card
- Test with no format param -> legality is None
- Test with empty deck -> returns zeroes
- Test budget section with priced and unpriced cards

### Frontend (10+ tests)
- Test DeckEvaluationPanel renders mana curve chart
- Test DeckEvaluationPanel renders type distribution pie
- Test DeckEvaluationPanel renders color distribution
- Test legality section: green badge for legal, red for illegal
- Test budget section: shows total value and top expensive cards
- Test loading state shows skeleton
- Test error state shows error message
- Test DeckView tab switching between Cards and Evaluation
- Test format dropdown changes evaluation
