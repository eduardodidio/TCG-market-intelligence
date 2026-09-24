/**
 * Deck suggestion types (F172). Mirrors the backend contract in
 * `src/api/schemas/deck_suggestions.py` — field names are snake_case as
 * returned by the API.
 */

export type SuggestionStatus = "pending" | "processing" | "done" | "failed";

export interface DeckSuggestionCreate {
  format_name: string;
  commander_card_id?: number | null;
  colors?: string[];
  archetype?: string | null;
  notes?: string | null;
}

export interface SuggestionSummary {
  total_cards: number;
  owned_cards: number;
  missing_cards: number;
  missing_cost_brl: number | null;
  unresolved_count: number;
}

export interface SuggestedCard {
  name_en: string;
  quantity: number;
  category: string;
  reason: string | null;
  card_id: number | null;
  set_code: string | null;
  collector_number: string | null;
  image_uri: string | null;
  is_owned: boolean;
  owned_quantity: number;
  missing_quantity: number;
  unit_price: number | null;
  missing_cost: number | null;
}

export interface SuggestionResult {
  deck_name: string;
  strategy: string;
  format_name: string;
  commander: { name_en: string; card_id: number | null } | null;
  cards: SuggestedCard[];
  summary: SuggestionSummary;
  unresolved: string[];
  warnings: string[];
  provider: string;
  model: string;
  generated_at: string;
}

export interface DeckSuggestion {
  id: number;
  format_name: string;
  commander_card_id: number | null;
  commander_name: string | null;
  colors: string[];
  archetype: string | null;
  notes: string | null;
  status: SuggestionStatus;
  error_message: string | null;
  saved_deck_id: number | null;
  created_at: string;
  processed_at: string | null;
  summary: SuggestionSummary | null;
  result?: SuggestionResult | null;
}

export interface DeckSuggestionSaveResult {
  deck_id: number;
}
