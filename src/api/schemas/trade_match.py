"""Trade matching API schemas (F110-T03/T04)."""

from __future__ import annotations

from pydantic import BaseModel


class DuplicateCard(BaseModel):
    card_id: int
    name_en: str | None
    name_pt: str | None = None
    set_code: str | None = None
    collector_number: str | None = None
    quantity: int
    surplus: int
    quality: str | None = None
    image_uri: str | None = None
    current_price: float | None = None


class MatchedCard(BaseModel):
    card_id: int
    name_en: str
    set_code: str | None = None
    image_uri: str | None = None
    partner_quantity: int
    your_max_price: float | None = None


class TradeMatch(BaseModel):
    partner_name: str
    share_code: str
    matching_card_count: int
    matched_cards: list[MatchedCard]
