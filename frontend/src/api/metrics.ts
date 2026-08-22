import type { ApiResponse, CardMetricsResponse } from "../types/api";
import { apiGet } from "./client";

export function fetchCardMetrics(
  entryId: number,
  period: string,
  currency: string,
): Promise<ApiResponse<CardMetricsResponse>> {
  return apiGet<CardMetricsResponse>(
    `/api/v1/collection/${entryId}/metrics`,
    { period, currency },
  );
}
