import type { ApiResponse } from "../types/api";
import { apiPost } from "./client";

export interface CatalogScanResponse {
  status: string;
  set_code: string;
  card_count: number;
  total_cost: number;
}

export interface ImportLigaResponse {
  status: string;
  card_id: number;
  card_name: string;
  message: string;
}

export function importLigaCard(
  url: string,
): Promise<ApiResponse<ImportLigaResponse>> {
  return apiPost<ImportLigaResponse>(
    "/api/v1/catalog/import-liga",
    { url },
    { timeoutMs: 15_000 },
  );
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
