"""Pydantic schemas for schedule management endpoints (F37)."""

from __future__ import annotations

from pydantic import BaseModel


class ScheduleCreateRequest(BaseModel):
    name: str
    cron_expression: str
    scan_type: str = "collection"
    filters_json: str = "{}"
    description: str | None = None
    max_retries: int = 3


class ScheduleUpdateRequest(BaseModel):
    name: str | None = None
    cron_expression: str | None = None
    scan_type: str | None = None
    filters_json: str | None = None
    description: str | None = None
    status: str | None = None  # active | paused
    max_retries: int | None = None


class ScheduleResponse(BaseModel):
    id: int
    name: str
    description: str | None
    cron_expression: str
    scan_type: str
    filters_json: str
    status: str
    last_run_id: int | None
    last_run_at: str | None
    next_run_at: str | None
    error_count: int
    max_retries: int
    created_at: str
    updated_at: str


class ScheduleListResponse(BaseModel):
    schedules: list[ScheduleResponse]
    total: int


class ScheduleTriggerResponse(BaseModel):
    schedule_id: int
    scan_id: int
    status: str
