import type { ApiResponse } from "../types/api";
import { apiGet, apiPost } from "./client";

export interface NewsItem {
  id: number;
  title: string;
  summary: string | null;
  source_url: string;
  source_name: string;
  category: string;
  image_url: string | null;
  published_at: string | null;
  fetched_at: string | null;
  is_read: boolean;
}

export interface NewsListResponse {
  items: NewsItem[];
  total: number;
}

export interface UnreadCountResponse {
  count: number;
}

export function fetchNews(
  params?: Record<string, string>,
): Promise<ApiResponse<NewsListResponse>> {
  return apiGet<NewsListResponse>("/api/v1/news", params);
}

export function markNewsRead(
  newsId: number,
): Promise<ApiResponse<{ marked: boolean }>> {
  return apiPost<{ marked: boolean }>(`/api/v1/news/${newsId}/mark-read`, {});
}

export function markNewsUnread(
  newsId: number,
): Promise<ApiResponse<{ marked: boolean }>> {
  return apiPost<{ marked: boolean }>(
    `/api/v1/news/${newsId}/mark-unread`,
    {},
  );
}

export function fetchUnreadCount(): Promise<
  ApiResponse<UnreadCountResponse>
> {
  return apiGet<UnreadCountResponse>("/api/v1/news/unread-count");
}
