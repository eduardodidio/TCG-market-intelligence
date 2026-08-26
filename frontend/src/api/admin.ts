import { apiGet, apiPatch } from "./client";

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

export function fetchAdminUsers(limit = 50, offset = 0) {
  return apiGet<AdminUser[]>("/api/v1/admin/users", {
    limit: String(limit),
    offset: String(offset),
  });
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
