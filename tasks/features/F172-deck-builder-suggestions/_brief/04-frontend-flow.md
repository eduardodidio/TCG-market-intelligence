# 04 — Frontend flow

Stack: React 19 + TS + Vite + Tailwind (dark slate/cyan palette, see `DeckBuildWizard.tsx`), `react-i18next`
with `t(key, { defaultValue })`, vitest + @testing-library/react. Tests mock `react-i18next` and the API modules
(see `frontend/src/pages/__tests__/DeckBuildWizard.test.tsx`). HTTP helpers: `apiGet`, `apiPost`, `apiPatch`, `apiDelete`
in `frontend/src/api/client.ts`, which return `ApiResponse<T>` = `{ data, errors, meta }`.

**No change to `App.tsx` or `Layout.tsx`.** Mode is chosen inside `/decks/build` and persisted in the URL
with `useSearchParams`: `?mode=manual` | `?mode=suggestion`. No param → chooser.

## New files

```
frontend/src/types/deckSuggestions.ts                     (T07)
frontend/src/api/deckSuggestions.ts                       (T07)
frontend/src/components/decks/CommanderSearch.tsx         (T06)
frontend/src/components/decks/DeckBuildModeChooser.tsx    (T10)
frontend/src/components/decks/SuggestionRequestForm.tsx   (T11)
frontend/src/components/decks/SuggestionRequestList.tsx   (T12)
frontend/src/components/decks/SuggestionResultView.tsx    (T13)
frontend/src/components/decks/DeckSuggestionPanel.tsx     (T14)
tests under frontend/src/components/decks/__tests__/ and frontend/src/api/__tests__/
```

## Types (T07)

```ts
export type SuggestionStatus = "pending" | "processing" | "done" | "failed";
export interface DeckSuggestionCreate { format_name: string; commander_card_id?: number | null; colors?: string[]; archetype?: string | null; notes?: string | null; }
export interface SuggestionSummary { total_cards: number; owned_cards: number; missing_cards: number; missing_cost_brl: number | null; unresolved_count: number; }
export interface SuggestedCard { name_en: string; quantity: number; category: string; reason: string | null; card_id: number | null; set_code: string | null; collector_number: string | null; image_uri: string | null; is_owned: boolean; owned_quantity: number; missing_quantity: number; unit_price: number | null; missing_cost: number | null; }
export interface SuggestionResult { deck_name: string; strategy: string; format_name: string; commander: { name_en: string; card_id: number | null } | null; cards: SuggestedCard[]; summary: SuggestionSummary; unresolved: string[]; warnings: string[]; provider: string; model: string; generated_at: string; }
export interface DeckSuggestion { id: number; format_name: string; commander_card_id: number | null; commander_name: string | null; colors: string[]; archetype: string | null; notes: string | null; status: SuggestionStatus; error_message: string | null; saved_deck_id: number | null; created_at: string; processed_at: string | null; summary: SuggestionSummary | null; result?: SuggestionResult | null; }
```

API functions: `createDeckSuggestion(body)`, `listDeckSuggestions(status?)`, `getDeckSuggestion(id)`,
`saveDeckSuggestion(id, deckName?)` → `{deck_id}`, `deleteDeckSuggestion(id)`. Base path `/api/v1/deck-suggestions`.

## Components

- **DeckBuildModeChooser** (`onChoose(mode: "manual" | "suggestion")`): two large cards.
  "Montar meu próprio deck" (the generator runs right away) and "Sugestão de deck" (Claude builds it from your collection;
  it is processed once a day). testids `mode-option-manual`, `mode-option-suggestion`.
- **SuggestionRequestForm** (`onCreated(s: DeckSuggestion)`): format select (commander, standard, pioneer, modern,
  legacy, vintage, pauper, casual).
  Commander → `<CommanderSearch>` + notes textarea (max 1000, shows a counter).
  Others → color toggles (WUBRG + "C" colorless, mutually exclusive with the colors) + archetype cards (aggro, control, midrange,
  combo, tempo, ramp) + notes. The submit is disabled until the form is valid. On success it shows a
  "Pedido registrado! Sua sugestão será gerada na próxima execução diária." banner and calls `onCreated`.
  API errors (400/429) are shown inline. testids `suggestion-form`, `suggestion-format-{f}`, `suggestion-color-{c}`,
  `suggestion-archetype-{a}`, `suggestion-notes`, `suggestion-submit`, `suggestion-success`, `suggestion-error`.
- **SuggestionRequestList** (`items`, `selectedId`, `onSelect`, `onRefresh`, `onDelete`, `loading`): rows show the format,
  commander or colors + archetype, a status badge (pending = amber "Na fila", processing = cyan "Processando",
  done = green "Pronto", failed = red "Falhou" + error tooltip), and the created date.
  Pending rows have a delete button. There is a refresh button and an empty state.
  testids `suggestion-list`, `suggestion-row-{id}`, `suggestion-status-{id}`, `suggestion-delete-{id}`, `suggestion-refresh`.
- **SuggestionResultView** (`suggestion: DeckSuggestion`, `onSaved(deckId)`):
  pending/processing → info message. failed → error message.
  done → strategy text, summary tiles (total, owned, missing, "Custo para completar R$ x"), warnings,
  cards grouped by `category`. Each card shows qty, name, an owned badge (green) or missing with the price (`R$ 0,00`
  pt-BR format via `toLocaleString("pt-BR", {style:"currency", currency:"BRL"})`), and the list of unresolved names.
  "Salvar como deck" button (deck name input prefilled) → `saveDeckSuggestion` → `navigate(/decks/{id})`.
  If `saved_deck_id` is set, it shows "Ver deck salvo" instead.
  testids `suggestion-result`, `suggestion-summary`, `suggestion-card-{i}`, `suggestion-save-btn`, `suggestion-view-deck`.
- **DeckSuggestionPanel**: composes the form (top), the list (left/top on mobile), and the result (right).
  It loads the list on mount, prepends a new request after `onCreated`, and fetches the detail (`getDeckSuggestion`) when a row is selected.
  Mobile-first: single column < md.

## Wizard integration (T14)

`DeckBuildWizard.tsx`: read `mode` from `useSearchParams`.
- no mode → render `<DeckBuildModeChooser onChoose={m => setSearchParams({mode: m})} />` (keep breadcrumb + title).
- `manual` → the existing 4-step wizard (unchanged behavior, still `data-testid="page-deck-build-wizard"` at the root).
- `suggestion` → `<DeckSuggestionPanel />`.
- A "Trocar modo" link clears the param.
Existing wizard tests must render with `?mode=manual` (`MemoryRouter initialEntries={["/decks/build?mode=manual"]}`).
