import type {
  ApiResponse,
  CommanderSearchResult,
  DeckDetail,
  DeckEvaluation,
  DeckGenerateParams,
  DeckGenerateResult,
  DeckImportResult,
  DeckSummary,
} from "../types/api";
import { apiDelete, apiGet, apiPost } from "./client";

export function fetchDecks(): Promise<ApiResponse<DeckSummary[]>> {
  return apiGet<DeckSummary[]>("/api/v1/decks");
}

export function fetchDeck(id: number): Promise<ApiResponse<DeckDetail>> {
  return apiGet<DeckDetail>(`/api/v1/decks/${id}`);
}

export function importDeck(
  name: string,
  format: "text" | "csv",
  content: string,
  description?: string,
): Promise<ApiResponse<DeckImportResult>> {
  return apiPost<DeckImportResult>("/api/v1/decks", {
    name,
    format,
    content,
    description: description || null,
  });
}

export async function deleteDeck(id: number): Promise<void> {
  return apiDelete(`/api/v1/decks/${id}`);
}

export function fetchDeckEvaluation(
  deckId: number,
  format?: string,
): Promise<ApiResponse<DeckEvaluation>> {
  const params: Record<string, string> = {};
  if (format) params.format = format;
  return apiGet<DeckEvaluation>(`/api/v1/decks/${deckId}/evaluate`, params);
}

export function generateDeck(
  params: DeckGenerateParams,
): Promise<ApiResponse<DeckGenerateResult>> {
  return apiPost<DeckGenerateResult>("/api/v1/decks/generate", params, {
    timeoutMs: 30_000,
  });
}

export function searchCommanders(
  query: string,
  colors?: string[],
): Promise<ApiResponse<CommanderSearchResult[]>> {
  const params: Record<string, string> = {};
  if (query) params.q = query;
  if (colors && colors.length > 0) params.colors = colors.join(",");
  return apiGet<CommanderSearchResult[]>("/api/v1/decks/commanders", params);
}
