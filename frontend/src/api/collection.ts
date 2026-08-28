import type { ApiResponse, BulkCanonizeResult, CollectionCard, CollectionCardDetail, CollectionSummary, PriceHistoryResponse } from "../types/api";
import { apiGet, apiPatch, apiPost } from "./client";

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

export function refreshCardPriceLiga(
  entryId: number,
  params?: Record<string, string>,
): Promise<ApiResponse<CollectionCardDetail>> {
  const query = params ? "?" + new URLSearchParams(params).toString() : "";
  return apiPost<CollectionCardDetail>(
    `/api/v1/collection/${entryId}/refresh-liga${query}`,
    {},
    { timeoutMs: 45000 },
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

export function canonizeAll(
  limit?: number,
): Promise<ApiResponse<BulkCanonizeResult>> {
  const query = limit != null ? `?limit=${limit}` : "";
  return apiPost<BulkCanonizeResult>(
    `/api/v1/collection/canonize-all${query}`,
    {},
    { timeoutMs: 120_000 },
  );
}

export function setManualPrice(
  entryId: number,
  price: number,
  currency: string,
): Promise<ApiResponse<CollectionCardDetail>> {
  return apiPatch<CollectionCardDetail>(
    `/api/v1/collection/${entryId}/price`,
    { price, currency },
  );
}

export interface ValuationData {
  current_value: number | null;
  previous_value: number | null;
  change_pct: number | null;
  change_abs: number | null;
  currency: string;
  snapshots: {
    date: string;
    value: number | null;
    priced_count: number;
    total_count: number;
  }[];
}

export function fetchValuation(
  days: number = 7,
  currency: string = "BRL",
): Promise<ApiResponse<ValuationData>> {
  const params: Record<string, string> = { days: String(days) };
  if (currency !== "BRL") params.currency = currency;
  return apiGet<ValuationData>("/api/v1/collection/valuation", params);
}

export function fetchCollectionSets(): Promise<
  ApiResponse<{ set_code: string; set_name: string | null; count: number }[]>
> {
  return apiGet("/api/v1/collection/sets");
}
