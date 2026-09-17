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
    total_value: float | None = None
    value_change_pct: float | None = None
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


# --- Deck Evaluation schemas (F133-T03) ---


class ManaCurvePoint(BaseModel):
    cmc: int
    count: int


class TypeDistEntry(BaseModel):
    type_name: str
    count: int


class ColorDistEntry(BaseModel):
    color: str
    pip_count: int


class IllegalCard(BaseModel):
    name_en: str
    status: str


class LegalityResult(BaseModel):
    format: str
    is_legal: bool
    illegal_cards: list[IllegalCard] = []
    singleton_violations: list[str] = []
    card_count_valid: bool = True


class BudgetEntry(BaseModel):
    name_en: str
    price: float
    quantity: int


class BudgetAnalysis(BaseModel):
    total_value: float
    most_expensive: list[BudgetEntry] = []
    price_tiers: dict[str, int] = {}


class DeckEvaluationResponse(BaseModel):
    deck_id: int
    mana_curve: list[ManaCurvePoint] = []
    type_distribution: list[TypeDistEntry] = []
    color_distribution: list[ColorDistEntry] = []
    land_count: int = 0
    nonland_count: int = 0
    total_cards: int = 0
    avg_cmc: float = 0.0
    color_identity: list[str] = []
    legality: LegalityResult | None = None
    budget: BudgetAnalysis | None = None
    suggestions: list[str] = []


# --- Deck Generator schemas (F133-T04) ---


class DeckGenerateRequest(BaseModel):
    format_name: str
    commander_card_id: int | None = None
    colors: list[str] = Field(default_factory=list)
    archetype: str | None = None
    budget_limit: float | None = None
    prioritize_owned: bool = False
    deck_name: str | None = None
    exclude_card_ids: list[int] = Field(default_factory=list)


class GeneratedCardSchema(BaseModel):
    card_id: int | None = None
    name_en: str
    set_code: str | None = None
    collector_number: str | None = None
    quantity: int = 1
    mana_cost: str | None = None
    type_line: str | None = None
    rarity: str | None = None
    image_uri: str | None = None
    price: float | None = None
    is_owned: bool = False


class DeckGenerateResponse(BaseModel):
    deck_id: int
    name: str
    format_name: str
    archetype: str | None = None
    colors: list[str] = []
    total_cards: int = 0
    land_count: int = 0
    nonland_count: int = 0
    total_value: float | None = None
    warnings: list[str] = []
    cards: list[GeneratedCardSchema] = []


class CommanderCandidate(BaseModel):
    card_id: int
    name_en: str
    set_code: str | None = None
    collector_number: str | None = None
    color_identity: str | None = None
    mana_cost: str | None = None
    type_line: str | None = None
    rarity: str | None = None
    image_uri: str | None = None
