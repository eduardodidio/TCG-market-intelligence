"""Wishlist API schemas (F110-T02)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WishlistAddRequest(BaseModel):
    card_id: int
    notes: str | None = None
    max_price: float | None = Field(None, ge=0)


class WishlistItem(BaseModel):
    id: int
    card_id: int
    name_en: str
    name_pt: str | None
    set_code: str | None
    collector_number: str | None
    notes: str | None
    max_price: float | None
    is_acquired: bool
    acquired_at: str | None
    created_at: str
    image_uri: str | None = None
    current_price: float | None = None


class WishlistCheckResponse(BaseModel):
    wishlisted: list[int]
