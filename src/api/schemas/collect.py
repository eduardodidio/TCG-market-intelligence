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


class CollectionHealth(BaseModel):
    last_collection_at: str | None
    next_expected_at: str | None
    total_cards: int
    stale_cards_count: int
    recent_errors_count: int
    status: str  # "healthy" | "stale" | "error"
