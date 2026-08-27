"""Pydantic schemas for the marketplace API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class SharingToggle(BaseModel):
    is_shared: bool


class MarketplaceListing(BaseModel):
    share_code: str
    entry_id: int
    card_name_en: str
    card_name_pt: str | None = None
    set_code: str
    collector_number: str
    rarity: str | None = None
    quantity: int = 1
    latest_price: Decimal | None = None
    estimated_fee: int


class TradeInterestRequest(BaseModel):
    share_code: str
    entry_id: int
    message: str | None = None


class TradeResponse(BaseModel):
    action: str  # "accept" or "reject"


class TradeDetail(BaseModel):
    id: int
    card_name: str
    set_code: str
    collector_number: str
    counterparty_share_code: str | None = None
    status: str
    estimated_fee: int
    my_role: str  # "buyer" or "seller"
    counterparty_email: str | None = None  # only after completion
    created_at: datetime


class SharingStatus(BaseModel):
    is_shared: bool
    share_code: str
