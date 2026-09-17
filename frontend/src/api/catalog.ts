import type { ApiResponse } from "../types/api";
import { apiPost } from "./client";

export interface CatalogScanResponse {
  status: string;
  set_code: string;
  card_count: number;
  total_cost: number;
}

export function refreshCatalogSet(
  setCode: string,
): Promise<ApiResponse<CatalogScanResponse>> {
  return apiPost<CatalogScanResponse>(
    "/api/v1/catalog/scan",
    { set_code: setCode },
    { timeoutMs: 30_000 },
  );
}
