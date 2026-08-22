import type { ApiResponse, BannedCollectionCard, CardLegalityWithChange } from "../types/api";
import { apiGet } from "./client";

export function fetchCollectionBanned(
  params?: { format?: string; days?: number },
): Promise<ApiResponse<BannedCollectionCard[]>> {
  const query = new URLSearchParams();
  if (params?.format) query.set("format", params.format);
  if (params?.days) query.set("days", String(params.days));
  const qs = query.toString();
  return apiGet<BannedCollectionCard[]>(`/api/v1/collection/banned${qs ? `?${qs}` : ""}`);
}

export function fetchEntryLegalities(
  entryId: number,
  params?: { days?: number },
): Promise<ApiResponse<CardLegalityWithChange[]>> {
  const query = new URLSearchParams();
  if (params?.days) query.set("days", String(params.days));
  const qs = query.toString();
  return apiGet<CardLegalityWithChange[]>(`/api/v1/collection/${entryId}/legality${qs ? `?${qs}` : ""}`);
}
