import type {
  ScheduleResponse,
  ScheduleListResponse,
} from "../../src/types/api";

export function makeSchedule(
  overrides: Partial<ScheduleResponse> = {},
): ScheduleResponse {
  return {
    id: 1,
    name: "Daily Collection",
    description: "Scan all cards daily",
    cron_expression: "0 6 * * *",
    scan_type: "collection",
    filters_json: "{}",
    status: "active",
    last_run_id: null,
    last_run_at: null,
    next_run_at: "2026-08-22T06:00:00",
    error_count: 0,
    max_retries: 3,
    created_at: "2026-08-21T12:00:00",
    updated_at: "2026-08-21T12:00:00",
    ...overrides,
  };
}

export function mockScheduleListResponse(
  schedules?: ScheduleResponse[],
  total?: number,
): ScheduleListResponse {
  const list = schedules ?? [
    makeSchedule({ id: 1, name: "Daily Collection" }),
    makeSchedule({ id: 2, name: "Weekly Sets", status: "paused" }),
  ];
  return {
    schedules: list,
    total: total ?? list.length,
  };
}
