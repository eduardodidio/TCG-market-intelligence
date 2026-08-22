import type { ApiResponse } from "../types/api";
import type {
  BanImpactSchema,
  BanListEntry,
  CardBanHistoryEntry,
  CardLegality,
  LegalityHistoryResponse,
} from "../types/banlist";
import { apiGet, apiPost } from "./client";

export function fetchFormats(): Promise<ApiResponse<string[]>> {
  return apiGet<string[]>("/api/v1/banlist/formats");
}

export function fetchBanList(params: {
  format: string;
  status?: string;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<ApiResponse<BanListEntry[]>> {
  const query: Record<string, string> = { format: params.format };
  if (params.status) query.status = params.status;
  if (params.search) query.search = params.search;
  if (params.limit !== undefined) query.limit = String(params.limit);
  if (params.offset !== undefined) query.offset = String(params.offset);
  return apiGet<BanListEntry[]>("/api/v1/banlist", query);
}

export function fetchCardLegalities(
  cardId: number,
): Promise<ApiResponse<CardLegality[]>> {
  return apiGet<CardLegality[]>(`/api/v1/banlist/card/${cardId}`);
}

export function fetchBanHistoryPaginated(params: {
  format?: string;
  cardId?: number;
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
  offset?: number;
}): Promise<ApiResponse<LegalityHistoryResponse>> {
  const query: Record<string, string> = {};
  if (params.format) query.format = params.format;
  if (params.cardId !== undefined) query.card_id = String(params.cardId);
  if (params.dateFrom) query.date_from = params.dateFrom;
  if (params.dateTo) query.date_to = params.dateTo;
  if (params.limit !== undefined) query.limit = String(params.limit);
  if (params.offset !== undefined) query.offset = String(params.offset);
  return apiGet<LegalityHistoryResponse>("/api/v1/banlist/history", query);
}

export function fetchCardBanHistory(
  cardId: number,
): Promise<ApiResponse<CardBanHistoryEntry[]>> {
  return apiGet<CardBanHistoryEntry[]>(
    `/api/v1/banlist/card/${cardId}/history`,
  );
}

export function fetchBanImpact(
  cardId: number,
  windowDays?: number,
): Promise<ApiResponse<BanImpactSchema[]>> {
  const query: Record<string, string> = {};
  if (windowDays !== undefined) query.window_days = String(windowDays);
  return apiGet<BanImpactSchema[]>(
    `/api/v1/banlist/impact/${cardId}`,
    query,
  );
}

/** @deprecated Use fetchBanHistoryPaginated instead */
export function fetchLegalityHistory(params: {
  format?: string;
  cardId?: number;
  limit?: number;
}): Promise<ApiResponse<LegalityHistoryResponse>> {
  return fetchBanHistoryPaginated(params);
}

export function triggerBanlistSync(params: {
  bulk?: boolean;
  limit?: number;
}): Promise<ApiResponse<{ job_id: string; status: string; message: string }>> {
  return apiPost("/api/v1/banlist/sync", params);
}
