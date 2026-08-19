import type { ApiResponse, MarketStats, MoversResponse } from "../types/api";
import { apiGet } from "./client";

export function fetchMovers(
  params?: Record<string, string>,
): Promise<ApiResponse<MoversResponse>> {
  return apiGet<MoversResponse>("/api/v1/market/movers", params);
}

export function fetchMarketStats(): Promise<ApiResponse<MarketStats>> {
  return apiGet<MarketStats>("/api/v1/market/stats");
}
