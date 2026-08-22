import { apiGet, apiPost, apiPatch, apiDelete } from "./client";
import type {
  ApiResponse,
  ScheduleCreateRequest,
  ScheduleListResponse,
  ScheduleResponse,
  ScheduleTriggerResponse,
  ScheduleUpdateRequest,
} from "../types/api";

export function fetchSchedules(
  params?: Record<string, string>,
): Promise<ApiResponse<ScheduleListResponse>> {
  return apiGet<ScheduleListResponse>("/api/v1/schedules", params);
}

export function fetchSchedule(
  id: number,
): Promise<ApiResponse<ScheduleResponse>> {
  return apiGet<ScheduleResponse>(`/api/v1/schedules/${id}`);
}

export function createSchedule(
  body: ScheduleCreateRequest,
): Promise<ApiResponse<ScheduleResponse>> {
  return apiPost<ScheduleResponse>("/api/v1/schedules", body);
}

export function updateSchedule(
  id: number,
  body: ScheduleUpdateRequest,
): Promise<ApiResponse<ScheduleResponse>> {
  return apiPatch<ScheduleResponse>(`/api/v1/schedules/${id}`, body);
}

export function deleteSchedule(id: number): Promise<void> {
  return apiDelete(`/api/v1/schedules/${id}`);
}

export function triggerSchedule(
  id: number,
): Promise<ApiResponse<ScheduleTriggerResponse>> {
  return apiPost<ScheduleTriggerResponse>(
    `/api/v1/schedules/${id}/trigger`,
    {},
  );
}
