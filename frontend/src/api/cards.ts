import type { ApiResponse, CardDetail, CardSummary, PriceObservation } from "../types/api";
import { apiGet } from "./client";

export function fetchCards(
  params?: Record<string, string>,
): Promise<ApiResponse<CardSummary[]>> {
  return apiGet<CardSummary[]>("/api/v1/cards", params);
}

export function fetchCardDetail(
  id: number,
): Promise<ApiResponse<CardDetail>> {
  return apiGet<CardDetail>(`/api/v1/cards/${id}`);
}

export function fetchCardHistory(
  id: number,
  period?: string,
): Promise<ApiResponse<PriceObservation[]>> {
  const params: Record<string, string> = {};
  if (period) params.period = period;
  return apiGet<PriceObservation[]>(`/api/v1/cards/${id}/history`, params);
}
