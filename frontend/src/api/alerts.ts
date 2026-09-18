import type { ApiResponse } from "../types/api";
import type {
  AlertResponse,
  NotificationsListResponse,
  CreateAlertRequest,
  UpdateAlertRequest,
} from "../types/alerts";
import { apiDelete, apiGet, apiPatch, apiPost } from "./client";

export function fetchAlerts(
  params?: Record<string, string>,
): Promise<ApiResponse<AlertResponse[]>> {
  return apiGet<AlertResponse[]>("/api/v1/alerts", params);
}

export function createAlert(
  body: CreateAlertRequest,
): Promise<ApiResponse<AlertResponse>> {
  return apiPost<AlertResponse>("/api/v1/alerts", body);
}

export function updateAlert(
  alertId: number,
  body: UpdateAlertRequest,
): Promise<ApiResponse<AlertResponse>> {
  return apiPatch<AlertResponse>(`/api/v1/alerts/${alertId}`, body);
}

export function deleteAlert(alertId: number): Promise<void> {
  return apiDelete(`/api/v1/alerts/${alertId}`);
}

export function fetchNotifications(
  params?: Record<string, string>,
): Promise<ApiResponse<NotificationsListResponse>> {
  return apiGet<NotificationsListResponse>(
    "/api/v1/alerts/notifications",
    params,
  );
}

export function markAllNotificationsRead(): Promise<ApiResponse<{ marked_read: boolean }>> {
  return apiPatch<{ marked_read: boolean }>(
    "/api/v1/alerts/notifications/read",
    {},
  );
}
