import type {
  ApiResponse,
  DeckDetail,
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
