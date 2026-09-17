# F133-T06: Navigation + Integration

**Wave:** 2
**Status:** planned
**Depends on:** F133-T03, F133-T04

## User Story

As a user, I want to easily find the Deck Builder and Deck Evaluator
features from the sidebar navigation so that I can discover and use
them without hunting through menus.

## Description

Add "Build Deck" and "Deck Evaluator" links to the Beta Test nav
section in the sidebar, finalize DeckView integration with the
evaluation tab, add i18n keys, and update project documentation.

## Tasks

### 1. Navigation — Layout.tsx

Add two items to `BETA_NAV_ITEMS` array in
`frontend/src/components/Layout.tsx`:

```ts
{ to: "/decks/build", labelKey: "nav.buildDeck", requiresAuth: true, icon: ICONS.wrench },
{ to: "/decks/evaluate", labelKey: "nav.deckEvaluator", requiresAuth: true, icon: ICONS.beaker },
```

Add new icon constants to `ICONS`:
- `wrench`: Heroicons wrench icon path (for Build Deck)
- `beaker`: Heroicons beaker icon path (for Deck Evaluator)

Position them after the existing deck items ("My Decks", "Top Decks")
in the beta items list.

Note: The "/decks/evaluate" link navigates to the DeckList page with
an `?evaluate=true` query param, which prompts the user to select a
deck to evaluate. This avoids creating a standalone evaluator page
(evaluation is always in context of a specific deck).

### 2. DeckList Integration

Modify `frontend/src/pages/DeckList.tsx`:
- Add an "Evaluate" button next to each deck in the list
- Clicking "Evaluate" navigates to `/decks/{id}?tab=evaluation`
- If URL has `?evaluate=true`, show a banner: "Select a deck to
  evaluate"

### 3. DeckView Evaluation Tab

Finalize DeckView.tsx integration (started in T03):
- Read `?tab=evaluation` from URL params
- If present, default to the Evaluation tab instead of Cards tab
- Add tab buttons: "Cards" | "Evaluation" | "Value History"
  (the existing value panel becomes the third tab)
- Each tab is lazy-loaded (evaluation panel only fetches when active)

### 4. i18n Keys

Add to both `frontend/src/i18n/locales/en.json` and `pt-BR.json`:

```json
{
  "nav": {
    "buildDeck": "Build Deck" / "Montar Deck",
    "deckEvaluator": "Deck Evaluator" / "Avaliador de Deck"
  },
  "deckBuilder": {
    "title": "Deck Builder" / "Montador de Deck",
    "stepFormat": "Choose Format" / "Escolher Formato",
    "stepCommander": "Choose Commander" / "Escolher Comandante",
    "stepColors": "Choose Colors" / "Escolher Cores",
    "stepArchetype": "Archetype & Budget" / "Arquetipo e Orcamento",
    "stepReview": "Review Deck" / "Revisar Deck",
    "formatCommander": "Commander (100 cards, singleton)",
    "formatStandard": "Standard (60 cards, max 4 copies)",
    "formatModern": "Modern (60 cards, max 4 copies)",
    "formatLegacy": "Legacy (60 cards, max 4 copies)",
    "formatPauper": "Pauper (60 cards, commons only)",
    "formatCasual": "Casual (no restrictions)",
    "searchCommander": "Search for a commander..." / "Buscar comandante...",
    "archetypeAggro": "Aggro — Fast creatures, low curve",
    "archetypeControl": "Control — Answers and card draw",
    "archetypeMidrange": "Midrange — Balanced threats and answers",
    "archetypeCombo": "Combo — Synergy-driven win conditions",
    "archetypeTempo": "Tempo — Efficient threats with disruption",
    "budgetLabel": "Budget Limit (BRL)" / "Limite de Orcamento (BRL)",
    "budgetNoLimit": "No limit" / "Sem limite",
    "prioritizeOwned": "Prioritize cards I own" / "Priorizar cartas que possuo",
    "generateBtn": "Generate Deck" / "Gerar Deck",
    "regenerateBtn": "Regenerate" / "Gerar Novamente",
    "saveDeck": "Save Deck" / "Salvar Deck",
    "deckName": "Deck Name" / "Nome do Deck"
  },
  "deckEval": {
    "title": "Deck Evaluation" / "Avaliacao do Deck",
    "manaCurve": "Mana Curve" / "Curva de Mana",
    "typeDistribution": "Card Types" / "Tipos de Carta",
    "colorDistribution": "Color Distribution" / "Distribuicao de Cores",
    "legality": "Format Legality" / "Legalidade no Formato",
    "legalIn": "Legal in {{format}}" / "Legal em {{format}}",
    "notLegalIn": "Not legal in {{format}}" / "Nao legal em {{format}}",
    "budget": "Budget Analysis" / "Analise de Orcamento",
    "avgCmc": "Avg. Mana Cost" / "Custo de Mana Medio",
    "lands": "Lands" / "Terrenos",
    "nonlands": "Non-lands" / "Nao-terrenos",
    "suggestions": "Suggestions" / "Sugestoes",
    "noSuggestions": "No issues found!" / "Nenhum problema encontrado!",
    "mostExpensive": "Most Expensive Cards" / "Cartas Mais Caras",
    "priceTiers": "Price Tiers" / "Faixas de Preco",
    "tabCards": "Cards" / "Cartas",
    "tabEvaluation": "Evaluation" / "Avaliacao",
    "tabValue": "Value History" / "Historico de Valor",
    "selectFormat": "Evaluate for format" / "Avaliar para formato",
    "singletonViolations": "Singleton Violations" / "Violacoes de Unicidade",
    "illegalCards": "Illegal Cards" / "Cartas Ilegais",
    "selectDeckToEvaluate": "Select a deck to evaluate" / "Selecione um deck para avaliar"
  }
}
```

### 5. Routing

Ensure App.tsx has:
- `<Route path="/decks/build" element={<DeckBuildWizard />} />` BEFORE
  `<Route path="/decks/:id" ... />`
- The `/decks/evaluate` path redirects to `/decks?evaluate=true`

### 6. Documentation

- Update `README.md` with a note about Deck Builder and Evaluator
  features under the appropriate section
- Create or update Mermaid diagrams under `docs/diagrams/`:
  - `F133-architecture.mmd` — data flow from catalog -> builder ->
    deck storage, and deck -> evaluator -> response
  - `F133-journey.mmd` — user journey for building a deck (wizard
    steps) and evaluating a deck (tab flow)

## Dev Notes

- The "/decks/evaluate" nav link is a convenience entry point that
  takes the user to the deck list with a prompt to pick a deck. The
  actual evaluation happens on the DeckView page.
- Tab state in DeckView should be reflected in the URL query param
  (`?tab=cards|evaluation|value`) for deep linking and back-button
  support.
- The existing value panel in DeckView becomes a tab. The panel code
  does not change, it just moves into a conditional render block.
- Keep the nav item order logical: My Decks -> Top Decks -> Build
  Deck -> Deck Evaluator.

## Testing

### Frontend (15+ tests)
- Test "Build Deck" appears in Beta Test nav section
- Test "Deck Evaluator" appears in Beta Test nav section
- Test clicking "Build Deck" navigates to /decks/build
- Test clicking "Deck Evaluator" navigates to /decks with evaluate
  param
- Test DeckList shows evaluate banner when ?evaluate=true
- Test DeckList has evaluate button per deck
- Test DeckView has three tabs: Cards, Evaluation, Value History
- Test DeckView defaults to Cards tab
- Test DeckView defaults to Evaluation tab when ?tab=evaluation
- Test tab switching updates URL query param
- Test i18n keys render in English
- Test i18n keys render in Portuguese
- Test breadcrumb shows correctly on Build Deck page
- Test responsive nav: items visible on mobile menu

### Documentation
- F133-architecture.mmd exists and is valid Mermaid
- F133-journey.mmd exists and is valid Mermaid
- README.md updated with deck builder/evaluator mention
