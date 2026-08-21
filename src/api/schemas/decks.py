"""Pydantic schemas for deck endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DeckImportRequest(BaseModel):
    name: str = Field(min_length=1)
    format: Literal["text", "csv"] = "text"
    content: str = Field(min_length=1)
    description: str | None = None


class DeckImportResult(BaseModel):
    deck_id: int
    name: str
    cards_imported: int
    cards_linked: int


class DeckSummarySchema(BaseModel):
    id: int
    name: str
    description: str | None = None
    total_cards: int = 0
    unique_cards: int = 0
    owned_cards: int = 0
    ownership_pct: float = 0.0
    created_at: datetime
    updated_at: datetime


class DeckCardSchema(BaseModel):
    id: int
    name_en: str
    set_code: str | None = None
    collector_number: str | None = None
    quantity: int = 1
    card_id: int | None = None
    in_collection: bool = False
    owned_quantity: int = 0
    collection_entry_id: int | None = None
    image_url: str | None = None
    latest_price: float | None = None


class DeckDetailSchema(BaseModel):
    id: int
    name: str
    description: str | None = None
    cards: list[DeckCardSchema] = []
    total_cards: int = 0
    unique_cards: int = 0
    owned_cards: int = 0
    ownership_pct: float = 0.0
    created_at: datetime
    updated_at: datetime
