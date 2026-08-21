import { apiGet } from "./client";
import type { ApiResponse } from "../types/api";

export interface ExchangeRate {
  rate_date: string;
  from_currency: string;
  to_currency: string;
  rate: number;
  source: string;
}

export function fetchCurrentRate(): Promise<ApiResponse<ExchangeRate | null>> {
  return apiGet("/api/v1/exchange-rates/current");
}
