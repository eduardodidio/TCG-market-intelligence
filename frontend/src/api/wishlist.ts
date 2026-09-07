import type { ApiResponse } from "../types/api";
import type { WishlistItem, WishlistCheckResponse } from "../types/wishlist";
import { apiDelete, apiGet, apiPatch, apiPost } from "./client";

export function fetchWishlist(
  params?: Record<string, string>,
): Promise<ApiResponse<WishlistItem[]>> {
  return apiGet<WishlistItem[]>("/api/v1/wishlist", params);
}

export function addToWishlist(
  cardId: number,
  notes?: string,
  maxPrice?: number,
): Promise<ApiResponse<WishlistItem>> {
  return apiPost<WishlistItem>("/api/v1/wishlist", {
    card_id: cardId,
    notes: notes ?? null,
    max_price: maxPrice ?? null,
  });
}

export function removeFromWishlist(cardId: number): Promise<void> {
  return apiDelete(`/api/v1/wishlist/${cardId}`);
}

export function markWishlistAcquired(
  cardId: number,
): Promise<ApiResponse<{ acquired: boolean }>> {
  return apiPatch<{ acquired: boolean }>(
    `/api/v1/wishlist/${cardId}/acquire`,
    {},
  );
}

export function checkWishlist(
  cardIds: number[],
): Promise<ApiResponse<WishlistCheckResponse>> {
  return apiGet<WishlistCheckResponse>("/api/v1/wishlist/check", {
    card_ids: cardIds.join(","),
  });
}
