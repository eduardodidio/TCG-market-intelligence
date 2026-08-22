import type { ApiResponse } from "../types/api";
import type {
  BanListEntry,
  CardLegality,
  LegalityHistoryEntry,
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

export function fetchLegalityHistory(params: {
  format?: string;
  cardId?: number;
  limit?: number;
}): Promise<ApiResponse<LegalityHistoryEntry[]>> {
  const query: Record<string, string> = {};
  if (params.format) query.format = params.format;
  if (params.cardId !== undefined) query.card_id = String(params.cardId);
  if (params.limit !== undefined) query.limit = String(params.limit);
  return apiGet<LegalityHistoryEntry[]>("/api/v1/banlist/history", query);
}

export function triggerBanlistSync(params: {
  bulk?: boolean;
  limit?: number;
}): Promise<ApiResponse<{ job_id: string; status: string; message: string }>> {
  return apiPost("/api/v1/banlist/sync", params);
}
