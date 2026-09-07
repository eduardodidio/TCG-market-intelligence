import type { ApiResponse } from "../types/api";
import type { AchievementItem, AchievementCheckResponse } from "../types/achievements";
import { apiGet, apiPost } from "./client";

export function fetchAchievements(): Promise<ApiResponse<AchievementItem[]>> {
  return apiGet<AchievementItem[]>("/api/v1/achievements");
}

export function checkAchievements(): Promise<ApiResponse<AchievementCheckResponse>> {
  return apiPost<AchievementCheckResponse>("/api/v1/achievements/check", {});
}
