import type { ApiResponse, CollectionCard, CollectionCardDetail, CollectionSummary } from "../types/api";
import { apiGet } from "./client";

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

export function fetchCollectionSets(): Promise<
  ApiResponse<{ set_code: string; set_name: string | null; count: number }[]>
> {
  return apiGet("/api/v1/collection/sets");
}
