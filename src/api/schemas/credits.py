"""Pydantic schemas for the credits API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CreditBalanceResponse(BaseModel):
    balance: int
    last_bonus_at: datetime | None
    bonus_eligible: bool
    next_bonus_at: datetime | None
    bonus_amount: int
    is_admin: bool


class CreditTransactionSchema(BaseModel):
    id: int
    amount: int
    reason: str
    reference_id: str | None
    created_at: datetime


class ClaimBonusResponse(BaseModel):
    balance: int
    credited: int
