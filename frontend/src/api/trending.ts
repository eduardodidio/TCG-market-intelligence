import { apiGet } from "./client";
import type { ApiResponse, TrendingResponse, TickerItemData } from "../types/api";

export function fetchTrending(
  direction: "gainers" | "losers",
  params: { period?: string; limit?: string; currency?: string },
): Promise<ApiResponse<TrendingResponse>> {
  return apiGet<TrendingResponse>(`/api/v1/market/trending/${direction}`, params);
}

export async function fetchTickerData(
  currency: string,
  signal?: AbortSignal,
): Promise<TickerItemData[]> {
  try {
    const [gainersRes, losersRes] = await Promise.all([
      apiGet<TrendingResponse>("/api/v1/market/trending/gainers", {
        period: "7d",
        limit: "10",
        currency,
      }, { signal }),
      apiGet<TrendingResponse>("/api/v1/market/trending/losers", {
        period: "7d",
        limit: "10",
        currency,
      }, { signal }),
    ]);

    const gainers: TickerItemData[] = (gainersRes.data?.cards ?? []).map((c) => ({
      card_id: c.card_id,
      name_en: c.name_en,
      name_pt: c.name_pt,
      set_code: c.set_code,
      price_end: c.price_end,
      change_pct: c.change_pct,
      direction: "up" as const,
      currency: c.currency,
    }));

    const losers: TickerItemData[] = (losersRes.data?.cards ?? []).map((c) => ({
      card_id: c.card_id,
      name_en: c.name_en,
      name_pt: c.name_pt,
      set_code: c.set_code,
      price_end: c.price_end,
      change_pct: c.change_pct,
      direction: "down" as const,
      currency: c.currency,
    }));

    // Interleave: gainer, loser, gainer, loser...
    const result: TickerItemData[] = [];
    const maxLen = Math.max(gainers.length, losers.length);
    for (let i = 0; i < maxLen; i++) {
      if (i < gainers.length) result.push(gainers[i]);
      if (i < losers.length) result.push(losers[i]);
    }
    return result;
  } catch {
    return [];
  }
}
