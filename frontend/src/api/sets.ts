import type { ApiResponse, SetSummary } from "../types/api";
import { apiGet } from "./client";

export function fetchSets(): Promise<ApiResponse<SetSummary[]>> {
  return apiGet<SetSummary[]>("/api/v1/sets");
}
