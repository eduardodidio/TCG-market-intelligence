from __future__ import annotations

from pydantic import BaseModel


class SetSummary(BaseModel):
    set_code: str
    game: str
    card_count: int
