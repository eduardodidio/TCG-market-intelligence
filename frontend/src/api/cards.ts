import type { ApiResponse, CardDetail, CardSummary, PriceHistoryResponse, WebSearchResult } from "../types/api";
import { apiGet, apiPost } from "./client";

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

// T01: Batch price trends for sparkline charts
export interface PriceTrendEntry {
  prices: number[];
  change_pct: number | null;
}

export interface PriceTrendsResponse {
  trends: Record<string, PriceTrendEntry>;
}

export function fetchPriceTrends(
  cardIds: number[],
  days: number = 7,
): Promise<ApiResponse<PriceTrendsResponse>> {
  return apiGet<PriceTrendsResponse>("/api/v1/cards/price-trends", {
    card_ids: cardIds.join(","),
    days: String(days),
  });
}

export interface PriceRefreshResponse {
  status: string;
  request_id: number;
  card_id: number;
}

export function refreshCardPrice(
  cardId: number,
): Promise<ApiResponse<PriceRefreshResponse>> {
  return apiPost<PriceRefreshResponse>(
    `/api/v1/cards/${cardId}/refresh-price`,
    {},
    { timeoutMs: 30_000 },
  );
}

export interface PriceRequestStatus {
  status: "none" | "pending" | "processing" | "completed" | "failed";
  requested_at?: string;
  processed_at?: string;
  result_price?: number | null;
}

export function fetchPriceRequestStatus(
  cardId: number,
): Promise<ApiResponse<PriceRequestStatus>> {
  return apiGet<PriceRequestStatus>(
    `/api/v1/cards/${cardId}/price-request-status`,
  );
}

// ── F213-T07: Price history with variant resolution ──────────────

export interface PriceHistoryPoint {
  date: string;
  price: number;
  source: string;
}

export interface DetailedPriceHistory {
  card_id: number;
  variant: string;
  sources: string[];
  since: string | null;
  real_points: number;
  snapshot_points: number;
  data: PriceHistoryPoint[];
}

export function fetchDetailedPriceHistory(
  cardId: number,
  params?: { days?: number; currency?: string },
): Promise<ApiResponse<DetailedPriceHistory>> {
  const query: Record<string, string> = {};
  if (params?.days) query.days = String(params.days);
  if (params?.currency) query.currency = params.currency;
  return apiGet<DetailedPriceHistory>(
    `/api/v1/price-history/cards/${cardId}`,
    query,
  );
}

export interface PriceMetrics {
  card_id: number;
  variant: string;
  sources: string[];
  min_price: number | null;
  max_price: number | null;
  avg_price: number | null;
  current_price: number | null;
  data_points: number;
  trend: string | null;
  change_pct: number | null;
  real_points: number;
  snapshot_points: number;
}

export function fetchPriceMetrics(
  cardId: number,
  params?: { days?: number; currency?: string },
): Promise<ApiResponse<PriceMetrics>> {
  const query: Record<string, string> = {};
  if (params?.days) query.days = String(params.days);
  if (params?.currency) query.currency = params.currency;
  return apiGet<PriceMetrics>(
    `/api/v1/price-history/cards/${cardId}/metrics`,
    query,
  );
}

export function searchCardsWeb(
  query: string,
): Promise<ApiResponse<WebSearchResult[]>> {
  return apiGet<WebSearchResult[]>("/api/v1/cards/search-web", { q: query }, { timeoutMs: 35_000 });
}
