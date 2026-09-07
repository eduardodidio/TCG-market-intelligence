import type { ApiResponse } from "../types/api";
import type { DuplicateCard, TradeMatch } from "../types/tradeMatch";
import { apiGet } from "./client";

export function fetchDuplicates(
  params?: Record<string, string>,
): Promise<ApiResponse<DuplicateCard[]>> {
  return apiGet<DuplicateCard[]>("/api/v1/trade/duplicates", params);
}

export function fetchDuplicatesCount(): Promise<
  ApiResponse<{ count: number }>
> {
  return apiGet<{ count: number }>("/api/v1/trade/duplicates/count");
}

export function fetchTradeMatches(
  limit?: number,
): Promise<ApiResponse<TradeMatch[]>> {
  const params: Record<string, string> = {};
  if (limit !== undefined) params.limit = String(limit);
  return apiGet<TradeMatch[]>("/api/v1/trade/matches", params);
}

export function fetchReverseMatches(
  limit?: number,
): Promise<ApiResponse<TradeMatch[]>> {
  const params: Record<string, string> = {};
  if (limit !== undefined) params.limit = String(limit);
  return apiGet<TradeMatch[]>("/api/v1/trade/matches/reverse", params);
}
