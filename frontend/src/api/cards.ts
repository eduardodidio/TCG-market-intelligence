import type { ApiResponse, CardDetail, CardSummary, PriceHistoryResponse, WebSearchResult } from "../types/api";
import { apiGet } from "./client";

export function fetchCards(
  params?: Record<string, string>,
): Promise<ApiResponse<CardSummary[]>> {
  return apiGet<CardSummary[]>("/api/v1/cards", params);
}

export function fetchCardDetail(
  id: number,
  params?: Record<string, string>,
): Promise<ApiResponse<CardDetail>> {
  return apiGet<CardDetail>(`/api/v1/cards/${id}`, params);
}

export function fetchCardHistory(
  id: number,
  period?: string,
  currency?: string,
): Promise<ApiResponse<PriceHistoryResponse>> {
  const params: Record<string, string> = {};
  if (period) params.period = period;
  if (currency) params.currency = currency;
  return apiGet<PriceHistoryResponse>(`/api/v1/cards/${id}/history`, params);
}

export function searchCardsWeb(
  query: string,
): Promise<ApiResponse<WebSearchResult[]>> {
  return apiGet<WebSearchResult[]>("/api/v1/cards/search-web", { q: query }, { timeoutMs: 35_000 });
}
