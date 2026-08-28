"""Pydantic schemas for admin endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AdminUserRow(BaseModel):
    id: int
    email: str
    display_name: str | None
    is_admin: bool
    is_active: bool
    credit_balance: int
    created_at: datetime


class CreateUserRequest(BaseModel):
    email: str = Field(..., max_length=320)
    display_name: str | None = Field(None, max_length=200)


class CreateUserResponse(BaseModel):
    user_id: int
    email: str
    display_name: str | None
    temporary_password: str


class CreditAdjustRequest(BaseModel):
    amount: int = Field(..., description="Positive to grant, negative to revoke")
    reason: str | None = Field(None, max_length=200)


class CreditAdjustResponse(BaseModel):
    user_id: int
    new_balance: int
    amount_applied: int


class AdminDashboardResponse(BaseModel):
    total_users: int
    active_users: int
    admin_users: int
    total_credits_in_circulation: int
    total_credits_granted: int
    total_credits_spent: int
    total_collection_entries: int
    total_scans: int


class ErrorLogEntry(BaseModel):
    id: str
    timestamp: datetime
    level: str
    error_type: str
    message: str
    module: str | None = None
    function: str | None = None


class ErrorLogDetail(ErrorLogEntry):
    traceback: str | None = None
    line: int | None = None
    request_method: str | None = None
    request_path: str | None = None
    request_user_id: int | None = None
    request_id: str | None = None
    request_params: dict | None = None  # parsed from JSON string
    extra: dict | None = None  # parsed from JSON string
