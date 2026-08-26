import { apiGet, apiPost } from "./client";
import type { ApiResponse } from "../types/api";

export interface CreditBalanceResponse {
  balance: number;
  bonus_eligible: boolean;
  next_bonus_at: string | null;
  is_admin: boolean;
}

export interface CreditTransaction {
  id: number;
  amount: number;
  reason: string;
  created_at: string;
}

export interface CreditHistoryResponse {
  transactions: CreditTransaction[];
  total: number;
}

export interface ClaimBonusResponse {
  balance: number;
  credited: number;
}

export async function fetchCreditBalance(): Promise<
  ApiResponse<CreditBalanceResponse>
> {
  return apiGet<CreditBalanceResponse>("/api/v1/credits/balance");
}

export async function fetchCreditHistory(
  limit?: number,
  offset?: number,
): Promise<ApiResponse<CreditHistoryResponse>> {
  const params: Record<string, string> = {};
  if (limit !== undefined) params.limit = String(limit);
  if (offset !== undefined) params.offset = String(offset);
  return apiGet<CreditHistoryResponse>("/api/v1/credits/history", params);
}

export async function claimBonus(): Promise<ApiResponse<ClaimBonusResponse>> {
  return apiPost<ClaimBonusResponse>("/api/v1/credits/claim-bonus", {});
}
