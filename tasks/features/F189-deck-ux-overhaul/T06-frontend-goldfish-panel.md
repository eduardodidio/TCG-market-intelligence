# F189-T06 — Frontend: Goldfish tab on DeckView

**Feature:** F192
**Wave:** 1
**Status:** planned
**Parallel:** yes (can develop with mocked API; depends on T05 for integration)

## User Story

As a deck builder, I want to see a Goldfish simulation tab on my deck page that shows opening hand quality, mana curve analysis, and screw/flood rates, so I can optimize my deck's consistency without leaving the app.

## Dev Notes

### Files to MODIFY

**`frontend/src/pages/DeckView.tsx`**
- Extend the tab system from 2 tabs to 3:
  - Change `activeTab` type from `"cards" | "evaluation"` to `"cards" | "evaluation" | "goldfish"`
  - Add a third tab button labeled "Goldfish" (i18n: `decks.goldfishTab`)
  - Render `<GoldfishPanel deckId={Number(id)} />` when activeTab is "goldfish"
- Add lazy import or direct import for GoldfishPanel
- Tab bar styling: keep consistent with existing Cards | Evaluation tab buttons (lines ~100-120 in DeckView.tsx)

**`frontend/src/api/decks.ts`**
- Add `fetchGoldfish()` function:
  ```typescript
  export function fetchGoldfish(
    deckId: number,
    numSimulations?: number,
    turns?: number,
  ): Promise<ApiResponse<GoldfishResult>> {
    const params: Record<string, string> = {};
    if (numSimulations) params.num_simulations = String(numSimulations);
    if (turns) params.turns = String(turns);
    return apiPost<GoldfishResult>(`/api/v1/decks/${deckId}/goldfish`, undefined, { params });
  }
  ```
  Note: The endpoint is POST but takes query params for num_simulations/turns. Alternatively, send them as body. Match whatever T05 implements.

**`frontend/src/types/api.ts`**
- Add types:
  ```typescript
  export interface GoldfishSampleHand {
    cards: string[];
    quality: number;
    land_count: number;
  }

  export interface GoldfishResult {
    deck_id: number;
    opening_hand_quality: number;
    avg_mana_by_turn: number[];
    mana_screw_rate: number;
    mana_flood_rate: number;
    avg_spells_cast_by_turn: number[];
    sample_hands: GoldfishSampleHand[];
    total_simulations: number;
    total_turns: number;
  }
  ```

### Files to CREATE

**`frontend/src/components/GoldfishPanel.tsx`**
New component, visually consistent with DeckEvaluationPanel.

Structure:
```
GoldfishPanel
  +-- Loading skeleton (while fetching)
  +-- Error state with retry button
  +-- Results display:
      +-- Opening Hand Quality section
      |     +-- Circular gauge or progress bar (0-100%)
      |     +-- Label: "Opening Hand Quality" + percentage
      +-- Mana Curve by Turn section
      |     +-- Recharts LineChart (X: turn number, Y: avg lands in play)
      |     +-- Tooltip showing exact values
      +-- Screw/Flood Analysis section
      |     +-- Two percentage badges side by side:
      |     |     +-- "Mana Screw" with red-tinted badge if > 20%
      |     |     +-- "Mana Flood" with blue-tinted badge if > 20%
      +-- Spells Cast by Turn section
      |     +-- Recharts BarChart or LineChart (X: turn, Y: avg spells cast)
      +-- Sample Hands section
      |     +-- 3 cards grids (best / median / worst hand)
      |     +-- Each shows card names + quality score + land count
      |     +-- If card images available, show mini card images (reuse CardImage)
      +-- "Simulate Again" button
            +-- Calls fetchGoldfish again with fresh server-side random seed
            +-- Shows loading spinner while re-simulating
```

Props:
```typescript
interface GoldfishPanelProps {
  deckId: number;
}
```

State:
- `data: GoldfishResult | null`
- `loading: boolean`
- `error: string | null`

Behavior:
- Fetches goldfish data on mount (or when tab is first activated)
- "Simulate Again" button triggers a new fetch (POST creates new random seed server-side)
- Loading skeleton during fetch (similar to DeckEvaluationPanel pattern)
- Error state with retry (ErrorBanner + onRetry pattern from F159)

Charts (Recharts):
- Mana by turn: `<LineChart>` with `<Line>` for avg_mana_by_turn
- Spells by turn: `<BarChart>` or `<LineChart>` with `<Bar>`/`<Line>` for avg_spells_cast_by_turn
- Both charts use `<ResponsiveContainer>` for responsive sizing
- Dark mode compatible colors (already using Recharts elsewhere: DeckView value chart, DeckEvaluationPanel)

### i18n keys to add

**`frontend/src/i18n/locales/en.json`** (under `decks` section):
- `decks.goldfishTab`: "Goldfish"
- `decks.goldfish.title`: "Goldfish Simulator"
- `decks.goldfish.subtitle`: "Simulate solitaire draws to analyze deck consistency"
- `decks.goldfish.openingHandQuality`: "Opening Hand Quality"
- `decks.goldfish.manaByTurn`: "Average Mana Available by Turn"
- `decks.goldfish.spellsByTurn`: "Average Spells Cast by Turn"
- `decks.goldfish.screwRate`: "Mana Screw Rate"
- `decks.goldfish.floodRate`: "Mana Flood Rate"
- `decks.goldfish.sampleHands`: "Sample Hands"
- `decks.goldfish.bestHand`: "Best Hand"
- `decks.goldfish.medianHand`: "Median Hand"
- `decks.goldfish.worstHand`: "Worst Hand"
- `decks.goldfish.simulateAgain`: "Simulate Again"
- `decks.goldfish.simulating`: "Simulating..."
- `decks.goldfish.turn`: "Turn {{n}}"
- `decks.goldfish.lands`: "{{count}} lands"
- `decks.goldfish.quality`: "Quality: {{pct}}%"
- `decks.goldfish.simulations`: "Based on {{count}} simulations"

**`frontend/src/i18n/locales/pt-BR.json`** (under `decks` section):
- `decks.goldfishTab`: "Goldfish"
- `decks.goldfish.title`: "Simulador Goldfish"
- `decks.goldfish.subtitle`: "Simule compras solitarias para analisar a consistencia do deck"
- `decks.goldfish.openingHandQuality`: "Qualidade da Mao Inicial"
- `decks.goldfish.manaByTurn`: "Mana Disponivel por Turno"
- `decks.goldfish.spellsByTurn`: "Magias Conjuradas por Turno"
- `decks.goldfish.screwRate`: "Taxa de Mana Screw"
- `decks.goldfish.floodRate`: "Taxa de Mana Flood"
- `decks.goldfish.sampleHands`: "Maos de Exemplo"
- `decks.goldfish.bestHand`: "Melhor Mao"
- `decks.goldfish.medianHand`: "Mao Mediana"
- `decks.goldfish.worstHand`: "Pior Mao"
- `decks.goldfish.simulateAgain`: "Simular Novamente"
- `decks.goldfish.simulating`: "Simulando..."
- `decks.goldfish.turn`: "Turno {{n}}"
- `decks.goldfish.lands`: "{{count}} terrenos"
- `decks.goldfish.quality`: "Qualidade: {{pct}}%"
- `decks.goldfish.simulations`: "Baseado em {{count}} simulacoes"

### Key constraints
- No new dependencies. Recharts is already installed and used (DeckView value chart, DeckEvaluationPanel).
- Charts must work in dark mode. Use `stroke` / `fill` colors from Tailwind theme or hardcoded dark-friendly values.
- GoldfishPanel should NOT auto-fetch on every tab switch if data is already loaded. Only re-fetch when "Simulate Again" is clicked.
- Mobile responsive: charts should stack vertically, sample hands should wrap.

### Edge cases
- Deck with 0 cards: GoldfishPanel should show an appropriate empty state message (the backend returns 400, so display the error)
- Very small deck (< 7 cards): sample hands will have fewer cards; display them correctly
- Long card names in sample hands: truncate with ellipsis
- Screw/flood rates of 0%: show green badge. Rates > 30%: show red/orange warning.

## Testing

- [ ] Unit test: `GoldfishPanel` renders loading skeleton initially
- [ ] Unit test: `GoldfishPanel` renders error state with retry button on API failure
- [ ] Unit test: `GoldfishPanel` renders opening hand quality gauge with correct percentage
- [ ] Unit test: `GoldfishPanel` renders mana by turn chart with correct data points
- [ ] Unit test: `GoldfishPanel` renders screw/flood rate badges
- [ ] Unit test: `GoldfishPanel` renders 3 sample hands with card names
- [ ] Unit test: `GoldfishPanel` "Simulate Again" button triggers re-fetch
- [ ] Unit test: `GoldfishPanel` shows loading state during re-simulation
- [ ] Unit test: `DeckView` renders Goldfish tab button
- [ ] Unit test: `DeckView` clicking Goldfish tab shows GoldfishPanel
- [ ] Unit test: `fetchGoldfish` API function sends correct request
- [ ] Manual: navigate to /decks/:id, click Goldfish tab, verify chart renders
- [ ] Manual: click "Simulate Again", verify new results appear
- [ ] Manual: verify dark mode renders charts correctly
- [ ] Manual: verify mobile layout stacks charts vertically
