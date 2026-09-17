import { API_BASE_URL } from "../utils/constants";

/* ---------- Types ---------- */

export interface ParsedMatch {
  id: string;
  card_name_parsed: string;
  card_name_collection: string | null;
  set_code_parsed: string | null;
  set_code_collection: string | null;
  collector_number: string | null;
  quantity_parsed: number;
  quantity_collection: number | null;
  unit_price: string;
  order_date: string | null;
  order_number: string;
  store_name: string;
  confidence: number;
  match_method: string;
  collection_entry_id: number | null;
  already_has_price: boolean;
  current_acquisition_price: string | null;
  selected: boolean;
}

export interface UnmatchedItem {
  card_name_parsed: string;
  set_code_parsed: string | null;
  unit_price: string;
  order_number: string;
  skip_reason: string;
}

export interface ImportPreviewResponse {
  total_files: number;
  total_orders: number;
  total_items_parsed: number;
  total_items_matched: number;
  total_items_unmatched: number;
  total_sealed_skipped: number;
  matches: ParsedMatch[];
  unmatched: UnmatchedItem[];
  warnings: string[];
}

export interface ApplyMatch {
  collection_entry_id: number;
  acquisition_price: string;
  acquired_at: string;
  overwrite: boolean;
}

export interface ApplyResultItem {
  collection_entry_id: number;
  card_name: string;
  acquisition_price: string;
  acquired_at: string | null;
}

export interface SkippedItem {
  collection_entry_id: number;
  card_name: string;
  reason: string;
}

export interface ApplyResponse {
  total_applied: number;
  total_skipped: number;
  applied: ApplyResultItem[];
  skipped: SkippedItem[];
}

/* ---------- API calls ---------- */

export async function uploadForPreview(
  files: File[],
  overwriteExisting: boolean,
): Promise<ImportPreviewResponse> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  const base = API_BASE_URL || window.location.origin;
  const url = `${base}/api/v1/purchases/import-preview?overwrite_existing=${overwriteExisting}`;

  const headers: Record<string, string> = {};
  const token = localStorage.getItem("tcg_access_token");
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => null);
    throw new Error(err?.detail || response.statusText);
  }

  return response.json();
}

export async function applyPurchases(
  matches: ApplyMatch[],
): Promise<ApplyResponse> {
  const base = API_BASE_URL || window.location.origin;
  const url = `${base}/api/v1/purchases/apply`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const token = localStorage.getItem("tcg_access_token");
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify({ matches }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => null);
    throw new Error(err?.detail || response.statusText);
  }

  return response.json();
}
