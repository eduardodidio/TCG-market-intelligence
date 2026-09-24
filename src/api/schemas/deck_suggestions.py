"""Schemas for the deck-suggestion request API (F172)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.deck_suggestions.repository import colors_from_str, load_result

SUGGESTION_FORMATS = {
    "commander",
    "standard",
    "pioneer",
    "modern",
    "legacy",
    "vintage",
    "pauper",
    "casual",
}
SUGGESTION_ARCHETYPES = {"aggro", "control", "midrange", "combo", "tempo", "ramp"}
SUGGESTION_STATUSES = ("pending", "processing", "done", "failed")
MAX_NOTES_LENGTH = 1000


class DeckSuggestionCreate(BaseModel):
    format_name: str
    commander_card_id: int | None = None
    colors: list[str] = Field(default_factory=list)
    archetype: str | None = None
    notes: str | None = Field(default=None, max_length=MAX_NOTES_LENGTH)


class DeckSuggestionSave(BaseModel):
    deck_name: str | None = Field(None, min_length=1, max_length=300)


class SuggestionSummary(BaseModel):
    total_cards: int
    owned_cards: int
    missing_cards: int
    missing_cost_brl: float | None = None
    unresolved_count: int = 0


class DeckSuggestionSchema(BaseModel):
    id: int
    format_name: str
    commander_card_id: int | None = None
    commander_name: str | None = None
    colors: list[str] = Field(default_factory=list)
    archetype: str | None = None
    notes: str | None = None
    status: Literal["pending", "processing", "done", "failed"]
    error_message: str | None = None
    saved_deck_id: int | None = None
    created_at: datetime
    processed_at: datetime | None = None
    summary: SuggestionSummary | None = None
    result: dict | None = None


class DeckSuggestionSavedResponse(BaseModel):
    deck_id: int


def _summary_from_result(result: dict | None) -> SuggestionSummary | None:
    if not result or not isinstance(result.get("summary"), dict):
        return None
    try:
        return SuggestionSummary(**result["summary"])
    except (TypeError, ValueError):
        return None


def to_schema(row, include_result: bool) -> DeckSuggestionSchema:
    """Convert a ``DeckSuggestionRequestRow`` into its API schema.

    ``summary`` is filled for done requests; the full ``result`` only when
    ``include_result`` is True (detail endpoint).
    """
    result = load_result(row) if row.status == "done" else None
    return DeckSuggestionSchema(
        id=row.id,
        format_name=row.format_name,
        commander_card_id=row.commander_card_id,
        commander_name=row.commander_name,
        colors=colors_from_str(row.colors),
        archetype=row.archetype,
        notes=row.notes,
        status=row.status,
        error_message=row.error_message,
        saved_deck_id=row.saved_deck_id,
        created_at=row.created_at,
        processed_at=row.processed_at,
        summary=_summary_from_result(result),
        result=result if include_result else None,
    )
