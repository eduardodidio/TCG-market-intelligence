import type { ApiResponse, CollectionHealth } from "../types/api";
import { apiGet } from "./client";

export function fetchCollectionHealth(): Promise<ApiResponse<CollectionHealth>> {
  return apiGet<CollectionHealth>("/api/v1/collect/health");
}
