import type { ApiResponse } from "../types/api";
import type {
  DeckSuggestion,
  DeckSuggestionCreate,
  DeckSuggestionSaveResult,
  SuggestionStatus,
} from "../types/deckSuggestions";
import { apiDelete, apiGet, apiPost } from "./client";

const BASE = "/api/v1/deck-suggestions";

/** Formats accepted by the backend (value + default label + expected card count). */
export const SUGGESTION_FORMATS: ReadonlyArray<{
  value: string;
  label: string;
  cardCount: number;
}> = [
  { value: "commander", label: "Commander", cardCount: 100 },
  { value: "standard", label: "Standard", cardCount: 60 },
  { value: "pioneer", label: "Pioneer", cardCount: 60 },
  { value: "modern", label: "Modern", cardCount: 60 },
  { value: "legacy", label: "Legacy", cardCount: 60 },
  { value: "vintage", label: "Vintage", cardCount: 60 },
  { value: "pauper", label: "Pauper", cardCount: 60 },
  { value: "casual", label: "Casual", cardCount: 60 },
];

/** Archetypes accepted by the backend (value + default label for i18n). */
export const SUGGESTION_ARCHETYPES: ReadonlyArray<{
  value: string;
  label: string;
}> = [
  { value: "aggro", label: "Aggro" },
  { value: "control", label: "Control" },
  { value: "midrange", label: "Midrange" },
  { value: "combo", label: "Combo" },
  { value: "tempo", label: "Tempo" },
  { value: "ramp", label: "Ramp" },
];

export const MTG_COLOR_KEYS = ["W", "U", "B", "R", "G"] as const;

export function createDeckSuggestion(
  body: DeckSuggestionCreate,
): Promise<ApiResponse<DeckSuggestion>> {
  return apiPost<DeckSuggestion>(BASE, body);
}

export function listDeckSuggestions(
  status?: SuggestionStatus,
): Promise<ApiResponse<DeckSuggestion[]>> {
  return apiGet<DeckSuggestion[]>(BASE, status ? { status } : undefined);
}

export function getDeckSuggestion(
  id: number,
): Promise<ApiResponse<DeckSuggestion>> {
  return apiGet<DeckSuggestion>(`${BASE}/${id}`);
}

export function saveDeckSuggestion(
  id: number,
  deckName?: string,
): Promise<ApiResponse<DeckSuggestionSaveResult>> {
  return apiPost<DeckSuggestionSaveResult>(
    `${BASE}/${id}/save`,
    deckName ? { deck_name: deckName } : {},
  );
}

export async function deleteDeckSuggestion(id: number): Promise<void> {
  return apiDelete(`${BASE}/${id}`);
}
