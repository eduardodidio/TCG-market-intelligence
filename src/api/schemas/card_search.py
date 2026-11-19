"""Schemas for web card search."""

from __future__ import annotations

from pydantic import BaseModel


class WebSearchResult(BaseModel):
    """A single card result from a web search."""

    card_name: str
    set_name: str | None = None
    normal_price: float | None = None
    foil_price: float | None = None
    image_url: str | None = None
    local_card_id: int | None = None  # populated if card exists locally
