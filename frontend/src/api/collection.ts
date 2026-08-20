import type { ApiResponse, CollectionCard, CollectionSummary } from "../types/api";
import { apiGet } from "./client";

export function fetchCollection(
  params?: Record<string, string>,
): Promise<ApiResponse<CollectionCard[]>> {
  return apiGet<CollectionCard[]>("/api/v1/collection", params);
}

export function fetchCollectionSummary(): Promise<ApiResponse<CollectionSummary>> {
  return apiGet<CollectionSummary>("/api/v1/collection/summary");
}

export function fetchCollectionSets(): Promise<
  ApiResponse<{ set_code: string; set_name: string | null; count: number }[]>
> {
  return apiGet("/api/v1/collection/sets");
}
