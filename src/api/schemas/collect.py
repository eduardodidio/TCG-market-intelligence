from __future__ import annotations

from pydantic import BaseModel, Field


class BackfillRequest(BaseModel):
    set: str = Field(..., alias="set")
    limit: int | None = None
    history_days: int = 1095


class UpdateRequest(BaseModel):
    set: str | None = None


class JobStatus(BaseModel):
    job_id: str
    status: str
    message: str
