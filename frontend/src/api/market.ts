import type { ApiResponse, MarketStats, MoversResponse, MarketSummaryResponse, TrendingResponse } from "../types/api";
import { apiGet } from "./client";

export function fetchMovers(
  params?: Record<string, string>,
): Promise<ApiResponse<MoversResponse>> {
  return apiGet<MoversResponse>("/api/v1/market/movers", params);
}

export function fetchMarketStats(
  params?: Record<string, string>,
): Promise<ApiResponse<MarketStats>> {
  return apiGet<MarketStats>("/api/v1/market/stats", params);
}

export function fetchMarketSummary(
  params?: Record<string, string>,
): Promise<ApiResponse<MarketSummaryResponse>> {
  return apiGet<MarketSummaryResponse>("/api/v1/market/summary", params);
}

export function fetchVolatile(
  params?: Record<string, string>,
): Promise<ApiResponse<TrendingResponse>> {
  return apiGet<TrendingResponse>("/api/v1/market/volatile", params);
}
