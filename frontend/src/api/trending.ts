import { apiGet } from "./client";
import type { ApiResponse, TrendingResponse } from "../types/api";

export function fetchTrending(
  direction: "gainers" | "losers",
  params: { period?: string; limit?: string; currency?: string },
): Promise<ApiResponse<TrendingResponse>> {
  return apiGet<TrendingResponse>(`/api/v1/market/trending/${direction}`, params);
}
