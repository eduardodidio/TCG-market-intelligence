import type { ApiResponse, CollectionCard, CollectionCardDetail, CollectionSummary, PriceHistoryResponse } from "../types/api";
import { apiGet, apiPost } from "./client";

export function fetchCollection(
  params?: Record<string, string>,
): Promise<ApiResponse<CollectionCard[]>> {
  return apiGet<CollectionCard[]>("/api/v1/collection", params);
}

export function fetchCollectionEntry(
  id: number,
  params?: Record<string, string>,
): Promise<ApiResponse<CollectionCardDetail>> {
  return apiGet<CollectionCardDetail>(`/api/v1/collection/${id}`, params);
}

export function fetchCollectionSummary(
  params?: Record<string, string>,
): Promise<ApiResponse<CollectionSummary>> {
  return apiGet<CollectionSummary>("/api/v1/collection/summary", params);
}

export function refreshCardPrice(
  entryId: number,
  params?: Record<string, string>,
): Promise<ApiResponse<CollectionCardDetail>> {
  const query = params ? "?" + new URLSearchParams(params).toString() : "";
  return apiPost<CollectionCardDetail>(
    `/api/v1/collection/${entryId}/refresh${query}`,
    {},
    { timeoutMs: 30000 },
  );
}

export function canonizeCard(
  entryId: number,
  params?: Record<string, string>,
): Promise<ApiResponse<CollectionCardDetail>> {
  const query = params ? "?" + new URLSearchParams(params).toString() : "";
  return apiPost<CollectionCardDetail>(
    `/api/v1/collection/${entryId}/canonize${query}`,
    {},
    { timeoutMs: 30000 },
  );
}

export function fetchCollectionHistory(
  entryId: number,
  period?: string,
  currency?: string,
): Promise<ApiResponse<PriceHistoryResponse>> {
  const params: Record<string, string> = {};
  if (period) params.period = period;
  if (currency) params.currency = currency;
  return apiGet<PriceHistoryResponse>(
    `/api/v1/collection/${entryId}/history`,
    params,
  );
}

export function fetchCollectionSets(): Promise<
  ApiResponse<{ set_code: string; set_name: string | null; count: number }[]>
> {
  return apiGet("/api/v1/collection/sets");
}
