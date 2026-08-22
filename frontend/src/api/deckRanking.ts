import type { ApiResponse, DeckRankingResponse, DeckValueDetail } from "../types/api";
import { apiGet } from "./client";

export function fetchDeckRanking(params: {
  sort_by?: string;
  sort_order?: string;
  period?: string;
  min_value?: number;
  max_value?: number;
  currency?: string;
  limit?: number;
  offset?: number;
}): Promise<ApiResponse<DeckRankingResponse>> {
  const query: Record<string, string> = {};
  if (params.sort_by) query.sort_by = params.sort_by;
  if (params.sort_order) query.sort_order = params.sort_order;
  if (params.period) query.period = params.period;
  if (params.min_value !== undefined) query.min_value = String(params.min_value);
  if (params.max_value !== undefined) query.max_value = String(params.max_value);
  if (params.currency) query.currency = params.currency;
  if (params.limit !== undefined) query.limit = String(params.limit);
  if (params.offset !== undefined) query.offset = String(params.offset);

  return apiGet<DeckRankingResponse>("/api/v1/decks/ranking", query);
}

export function fetchDeckValue(
  deckId: number,
  period?: string,
  currency?: string,
): Promise<ApiResponse<DeckValueDetail>> {
  const query: Record<string, string> = {};
  if (period) query.period = period;
  if (currency) query.currency = currency;

  return apiGet<DeckValueDetail>(`/api/v1/decks/${deckId}/value`, query);
}
