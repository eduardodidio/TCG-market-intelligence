"""Tests for deck API schemas."""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.api.schemas.decks import (
    DeckCardSchema,
    DeckDetailSchema,
    DeckImportRequest,
    DeckImportResult,
    DeckSummarySchema,
)


class TestDeckImportRequest:
    def test_valid_text(self):
        req = DeckImportRequest(name="My Deck", content="4 Lightning Bolt")
        assert req.format == "text"
        assert req.description is None

    def test_valid_csv(self):
        req = DeckImportRequest(
            name="CSV Deck", format="csv", content="Card (EN),Quantidade\nBolt,4"
        )
        assert req.format == "csv"

    def test_with_description(self):
        req = DeckImportRequest(name="Burn", content="4 Bolt", description="Fast aggro")
        assert req.description == "Fast aggro"

    def test_empty_name_fails(self):
        with pytest.raises(ValidationError):
            DeckImportRequest(name="", content="4 Bolt")

    def test_empty_content_fails(self):
        with pytest.raises(ValidationError):
            DeckImportRequest(name="Deck", content="")

    def test_invalid_format_fails(self):
        with pytest.raises(ValidationError):
            DeckImportRequest(name="Deck", format="json", content="data")


class TestDeckImportResult:
    def test_valid(self):
        result = DeckImportResult(deck_id=1, name="My Deck", cards_imported=10, cards_linked=5)
        assert result.deck_id == 1
        assert result.cards_linked == 5


class TestDeckSummarySchema:
    def test_valid(self):
        now = datetime(2026, 8, 21, 12, 0, 0)
        summary = DeckSummarySchema(
            id=1,
            name="Test",
            total_cards=60,
            unique_cards=15,
            owned_cards=10,
            ownership_pct=66.67,
            created_at=now,
            updated_at=now,
        )
        assert summary.total_cards == 60
        assert summary.description is None

    def test_defaults(self):
        now = datetime.now()
        summary = DeckSummarySchema(id=1, name="Test", created_at=now, updated_at=now)
        assert summary.total_cards == 0
        assert summary.ownership_pct == 0.0


class TestDeckCardSchema:
    def test_defaults(self):
        card = DeckCardSchema(id=1, name_en="Bolt")
        assert card.quantity == 1
        assert card.in_collection is False
        assert card.owned_quantity == 0
        assert card.card_id is None
        assert card.image_url is None
        assert card.latest_price is None

    def test_full(self):
        card = DeckCardSchema(
            id=1,
            name_en="Bolt",
            set_code="lea",
            collector_number="161",
            quantity=4,
            card_id=42,
            in_collection=True,
            owned_quantity=3,
            collection_entry_id=100,
            image_url="https://example.com",
            latest_price=5.0,
        )
        assert card.in_collection is True
        assert card.collection_entry_id == 100


class TestDeckDetailSchema:
    def test_valid(self):
        now = datetime(2026, 8, 21, 12, 0, 0)
        detail = DeckDetailSchema(
            id=1,
            name="Test",
            cards=[DeckCardSchema(id=1, name_en="Bolt")],
            total_cards=4,
            unique_cards=1,
            owned_cards=1,
            ownership_pct=100.0,
            created_at=now,
            updated_at=now,
        )
        assert len(detail.cards) == 1
        assert detail.total_cards == 4

    def test_empty_cards(self):
        now = datetime.now()
        detail = DeckDetailSchema(id=1, name="Empty", created_at=now, updated_at=now)
        assert detail.cards == []
