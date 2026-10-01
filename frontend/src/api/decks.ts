import type {
  ApiResponse,
  DeckCreateResult,
  DeckDetail,
  DeckEvaluation,
  DeckImportResult,
  DeckSummary,
  GoldfishResult,
} from "../types/api";
import { apiDelete, apiGet, apiPost, apiPut } from "./client";

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

export function createDeck(
  name: string,
  description?: string,
): Promise<ApiResponse<DeckCreateResult>> {
  return apiPost<DeckCreateResult>("/api/v1/decks/create", {
    name,
    description: description || null,
  });
}

export function updateDeck(
  id: number,
  data: { name?: string; description?: string },
): Promise<ApiResponse<DeckDetail>> {
  return apiPut<DeckDetail>(`/api/v1/decks/${id}`, data);
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

export function fetchGoldfish(
  deckId: number,
  numSimulations = 100,
  turns = 7,
): Promise<ApiResponse<GoldfishResult>> {
  const qs = `?num_simulations=${numSimulations}&turns=${turns}`;
  return apiPost<GoldfishResult>(`/api/v1/decks/${deckId}/goldfish${qs}`, undefined);
}
