import type { ApiResponse, BulkCanonizeResult, CollectionCard, CollectionCardDetail, CollectionSummary, ImportResult, PriceHistoryResponse } from "../types/api";
import { apiDelete, apiGet, apiPatch, apiPost } from "./client";

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

export function patchCollectionEntry(
  id: number,
  updates: { quantity?: number; quality?: string; language?: string; extras?: string },
): Promise<ApiResponse<CollectionCard>> {
  return apiPatch<CollectionCard>(`/api/v1/collection/${id}`, updates);
}

export async function deleteCollectionEntry(id: number): Promise<void> {
  return apiDelete(`/api/v1/collection/${id}`);
}

export function fetchCollectionSets(): Promise<
  ApiResponse<{ set_code: string; set_name: string | null; count: number }[]>
> {
  return apiGet("/api/v1/collection/sets");
}

// --- Batch operations ---

export interface ParsedLine {
  line_number: number;
  raw_text: string;
  quantity: number;
  name: string;
  set_code: string | null;
  quality: string | null;
  language: string | null;
  extras: string | null;
  error: string | null;
}

export interface BatchParseResult {
  entries: ParsedLine[];
}

export interface BatchAddEntry {
  name_en: string;
  set_code?: string;
  collector_number?: string;
  quantity?: number;
  quality?: string;
  language?: string;
  extras?: string;
}

export interface BatchAddError {
  line: number;
  text: string;
  error: string;
}

export interface BatchAddResult {
  added: number;
  errors: BatchAddError[];
}

export function parseBatchText(
  text: string,
): Promise<ApiResponse<BatchParseResult>> {
  return apiPost<BatchParseResult>("/api/v1/collection/batch/parse", { text });
}

export function addBatchEntries(
  entries: BatchAddEntry[],
): Promise<ApiResponse<BatchAddResult>> {
  return apiPost<BatchAddResult>("/api/v1/collection/batch", { entries });
}

// --- Bulk operations ---

export interface BulkUpdateResponse {
  affected: number;
}

export interface BulkDeleteResponse {
  deleted: number;
}

export function bulkUpdateEntries(
  ids: number[],
  updates: { quality?: string; language?: string; extras?: string },
): Promise<ApiResponse<BulkUpdateResponse>> {
  return apiPatch<BulkUpdateResponse>("/api/v1/collection/bulk", { ids, updates });
}

export function bulkDeleteEntries(
  ids: number[],
): Promise<ApiResponse<BulkDeleteResponse>> {
  return apiPost<BulkDeleteResponse>("/api/v1/collection/bulk-delete", { ids });
}

// --- CSV import ---

export async function importCollectionCsv(
  file: File,
): Promise<ApiResponse<ImportResult>> {
  const token = localStorage.getItem("tcg_access_token");
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/v1/collection/import", {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  return res.json();
}
