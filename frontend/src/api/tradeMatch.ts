import type { ApiResponse } from "../types/api";
import type { DuplicateCard, TradeMatch } from "../types/tradeMatch";
import { apiGet } from "./client";

export interface DuplicateSet {
  set_code: string | null;
  set_name: string | null;
  count: number;
}

export function fetchDuplicates(
  params?: Record<string, string>,
): Promise<ApiResponse<DuplicateCard[]>> {
  return apiGet<DuplicateCard[]>("/api/v1/trade/duplicates", params);
}

export function fetchDuplicateSets(): Promise<ApiResponse<DuplicateSet[]>> {
  return apiGet<DuplicateSet[]>("/api/v1/trade/duplicates/sets");
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
