import type { ApiResponse } from "../types/api";
import { apiGet, apiPost, apiDelete } from "./client";

export interface EvalEntry {
  id: number;
  card_name: string;
  set_code: string | null;
  collector_number: string | null;
  liga_url: string | null;
  price_at_add: number | null;
  card_id: number | null;
  image_url: string | null;
  created_at: string | null;
}

export interface EvalCreateBody {
  card_name: string;
  set_code?: string | null;
  collector_number?: string | null;
  liga_url?: string | null;
  source_data_json?: string | null;
  price_at_add?: number | null;
  card_id?: number | null;
}

export interface EvalPromoteResult {
  collection_entry_id: number;
  card_name: string;
}

export function fetchEvaluations(): Promise<ApiResponse<EvalEntry[]>> {
  return apiGet<EvalEntry[]>("/api/v1/evaluations");
}

export function createEvaluation(
  body: EvalCreateBody,
): Promise<ApiResponse<EvalEntry>> {
  return apiPost<EvalEntry>("/api/v1/evaluations", body);
}

export async function deleteEvaluation(id: number): Promise<void> {
  await apiDelete(`/api/v1/evaluations/${id}`);
}

export function promoteEvaluation(
  id: number,
): Promise<ApiResponse<EvalPromoteResult>> {
  return apiPost<EvalPromoteResult>(`/api/v1/evaluations/${id}/promote`, {});
}
