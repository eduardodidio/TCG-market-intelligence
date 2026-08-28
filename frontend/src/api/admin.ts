import { apiGet, apiPatch, apiPost } from "./client";
import type { ApiResponse } from "../types/api";
import { API_BASE_URL } from "../utils/constants";

export interface AdminUser {
  id: number;
  email: string;
  display_name: string | null;
  is_admin: boolean;
  is_active: boolean;
  credit_balance: number;
  created_at: string;
}

export interface AdminDashboard {
  total_users: number;
  active_users: number;
  admin_users: number;
  total_credits_in_circulation: number;
  total_credits_granted: number;
  total_credits_spent: number;
  total_collection_entries: number;
  total_scans: number;
}

export interface CreditAdjustResult {
  user_id: number;
  new_balance: number;
  amount_applied: number;
}

export interface CreateUserResult {
  user_id: number;
  email: string;
  display_name: string | null;
  temporary_password: string;
}

export function fetchAdminUsers(limit = 50, offset = 0) {
  return apiGet<AdminUser[]>("/api/v1/admin/users", {
    limit: String(limit),
    offset: String(offset),
  });
}

export function createUser(email: string, displayName?: string) {
  return apiPost<CreateUserResult>("/api/v1/admin/users", {
    email,
    display_name: displayName || null,
  });
}

export async function deleteUser(userId: number): Promise<ApiResponse<{ user_id: number; deleted: boolean }>> {
  const url = new URL(`/api/v1/admin/users/${userId}`, API_BASE_URL || window.location.origin);
  const headers: Record<string, string> = { Accept: "application/json" };
  const token = localStorage.getItem("tcg_access_token");
  if (token) headers["Authorization"] = `Bearer ${token}`;

  try {
    const response = await fetch(url.toString(), { method: "DELETE", headers });
    if (!response.ok) {
      const errorBody = await response.json().catch(() => null);
      if (errorBody && Array.isArray(errorBody.errors) && errorBody.errors.length > 0) {
        return errorBody as ApiResponse<{ user_id: number; deleted: boolean }>;
      }
      return {
        data: null,
        meta: { cursor: null, total: null, offset: null, request_id: "" },
        errors: [{ code: `HTTP_${response.status}`, message: errorBody?.detail || response.statusText }],
      };
    }
    return (await response.json()) as ApiResponse<{ user_id: number; deleted: boolean }>;
  } catch (err: unknown) {
    return {
      data: null,
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [{ code: "NETWORK_ERROR", message: err instanceof Error ? err.message : "Unknown error" }],
    };
  }
}

export function adjustUserCredits(
  userId: number,
  amount: number,
  reason?: string,
) {
  return apiPatch<CreditAdjustResult>(
    `/api/v1/admin/users/${userId}/credits`,
    { amount, reason },
  );
}

export function fetchAdminDashboard() {
  return apiGet<AdminDashboard>("/api/v1/admin/dashboard");
}

export interface ErrorLogEntry {
  id: string;
  timestamp: string;
  level: string;
  error_type: string;
  message: string;
  module: string | null;
  function: string | null;
}

export interface ErrorLogDetail extends ErrorLogEntry {
  traceback: string | null;
  line: number | null;
  request_method: string | null;
  request_path: string | null;
  request_user_id: number | null;
  request_id: string | null;
  request_params: Record<string, unknown> | null;
  extra: Record<string, unknown> | null;
}

export function fetchAdminErrors(params: {
  level?: string;
  module?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}) {
  const query: Record<string, string> = {};
  if (params.level) query.level = params.level;
  if (params.module) query.module = params.module;
  if (params.date_from) query.date_from = params.date_from;
  if (params.date_to) query.date_to = params.date_to;
  if (params.limit !== undefined) query.limit = String(params.limit);
  if (params.offset !== undefined) query.offset = String(params.offset);
  return apiGet<ErrorLogEntry[]>("/api/v1/admin/errors", query);
}

export function fetchAdminErrorDetail(errorId: string) {
  return apiGet<ErrorLogDetail>(`/api/v1/admin/errors/${errorId}`);
}
