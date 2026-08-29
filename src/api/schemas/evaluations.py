"""Pydantic schemas for evaluation list (watchlist) endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvalCreateRequest(BaseModel):
    card_name: str = Field(..., min_length=1, max_length=500)
    set_code: str | None = None
    collector_number: str | None = None
    liga_url: str | None = None
    source_data_json: str | None = None
    price_at_add: float | None = None
    card_id: int | None = None


class EvalEntryResponse(BaseModel):
    id: int
    card_name: str
    set_code: str | None
    collector_number: str | None
    liga_url: str | None
    price_at_add: float | None
    card_id: int | None
    image_url: str | None
    created_at: str | None


class EvalPromoteResponse(BaseModel):
    collection_entry_id: int
    card_name: str
