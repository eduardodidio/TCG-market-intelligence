import { API_BASE_URL } from "../utils/constants";

const DEFAULT_TIMEOUT_MS = 10_000;

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    "Content-Type": "application/json",
  };
  const token = localStorage.getItem("tcg_access_token");
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

function buildUrl(path: string, params?: Record<string, string>): string {
  const url = new URL(path, API_BASE_URL || window.location.origin);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== "") url.searchParams.set(k, v);
    }
  }
  return url.toString();
}

async function marketplaceGet<T>(path: string, params?: Record<string, string>): Promise<T> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);
  const resp = await fetch(buildUrl(path, params), {
    headers: authHeaders(),
    signal: controller.signal,
  });
  clearTimeout(id);
  if (!resp.ok) {
    const body = await resp.json().catch(() => null);
    throw new Error(body?.detail || resp.statusText);
  }
  return resp.json() as Promise<T>;
}

async function marketplacePost<T>(path: string, body: unknown): Promise<T> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);
  const resp = await fetch(buildUrl(path), {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(body),
    signal: controller.signal,
  });
  clearTimeout(id);
  if (!resp.ok) {
    const errBody = await resp.json().catch(() => null);
    throw new Error(errBody?.detail || resp.statusText);
  }
  return resp.json() as Promise<T>;
}

async function marketplacePatch<T>(path: string, body: unknown): Promise<T> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);
  const resp = await fetch(buildUrl(path), {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify(body),
    signal: controller.signal,
  });
  clearTimeout(id);
  if (!resp.ok) {
    const errBody = await resp.json().catch(() => null);
    throw new Error(errBody?.detail || resp.statusText);
  }
  return resp.json() as Promise<T>;
}

// --- Types ---

export interface MarketplaceListing {
  share_code: string;
  entry_id: number;
  card_name_en: string;
  card_name_pt: string | null;
  set_code: string;
  collector_number: string;
  rarity: string | null;
  quantity: number;
  latest_price: number | null;
  estimated_fee: number;
}

export interface ListingsResponse {
  listings: MarketplaceListing[];
  count: number;
}

export interface SharingStatus {
  is_shared: boolean;
  share_code: string | null;
}

export interface TradeInterestResult {
  id: number;
  status: string;
  estimated_fee: number;
  card_price: number | null;
}

export interface TradeRespondResult {
  id: number;
  status: string;
  agreement_id?: number;
}

export interface TradeConfirmResult {
  id: number;
  status: string;
  my_confirmed: boolean;
  both_confirmed: boolean;
  fee_charged?: number;
  buyer_email?: string;
  seller_email?: string;
}

export interface TradeDetail {
  id: number;
  card_name: string;
  set_code: string;
  collector_number: string;
  counterparty_share_code: string | null;
  status: string;
  estimated_fee: number;
  my_role: "buyer" | "seller";
  counterparty_email: string | null;
  created_at: string;
}

export interface MyTradesResponse {
  trades: TradeDetail[];
  count: number;
}

// --- API functions ---

export function fetchSharingStatus(): Promise<SharingStatus> {
  return marketplaceGet<SharingStatus>("/api/v1/marketplace/sharing");
}

export function toggleSharing(is_shared: boolean): Promise<SharingStatus> {
  return marketplacePatch<SharingStatus>("/api/v1/marketplace/sharing", { is_shared });
}

export function fetchListings(params?: Record<string, string>): Promise<ListingsResponse> {
  return marketplaceGet<ListingsResponse>("/api/v1/marketplace/listings", params);
}

export function expressInterest(
  share_code: string,
  entry_id: number,
  message?: string,
): Promise<TradeInterestResult> {
  return marketplacePost<TradeInterestResult>("/api/v1/marketplace/interest", {
    share_code,
    entry_id,
    message: message || null,
  });
}

export function respondToInterest(
  interestId: number,
  action: "accept" | "reject",
): Promise<TradeRespondResult> {
  return marketplacePost<TradeRespondResult>(
    `/api/v1/marketplace/respond/${interestId}`,
    { action },
  );
}

export function confirmAgreement(interestId: number): Promise<TradeConfirmResult> {
  return marketplacePost<TradeConfirmResult>(
    `/api/v1/marketplace/agree/${interestId}`,
    {},
  );
}

export function fetchMyTrades(params?: Record<string, string>): Promise<MyTradesResponse> {
  return marketplaceGet<MyTradesResponse>("/api/v1/marketplace/my-trades", params);
}
