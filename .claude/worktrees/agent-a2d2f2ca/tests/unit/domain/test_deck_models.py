"""Tests for DeckSummary and DeckCardDetail domain models."""

from __future__ import annotations

from datetime import datetime

from src.domain.models import DeckCardDetail, DeckSummary


class TestDeckSummary:
    def test_defaults(self):
        summary = DeckSummary(id=1, name="Test Deck")
        assert summary.id == 1
        assert summary.name == "Test Deck"
        assert summary.description is None
        assert summary.total_cards == 0
        assert summary.unique_cards == 0
        assert summary.owned_cards == 0
        assert summary.ownership_pct == 0.0
        assert isinstance(summary.created_at, datetime)
        assert isinstance(summary.updated_at, datetime)

    def test_full_values(self):
        now = datetime(2026, 8, 21, 12, 0, 0)
        summary = DeckSummary(
            id=5,
            name="Burn",
            description="Red aggro",
            total_cards=60,
            unique_cards=15,
            owned_cards=10,
            ownership_pct=66.67,
            created_at=now,
            updated_at=now,
        )
        assert summary.total_cards == 60
        assert summary.unique_cards == 15
        assert summary.owned_cards == 10
        assert summary.ownership_pct == 66.67
        assert summary.description == "Red aggro"


class TestDeckCardDetail:
    def test_defaults(self):
        card = DeckCardDetail(id=1, name_en="Lightning Bolt")
        assert card.id == 1
        assert card.name_en == "Lightning Bolt"
        assert card.set_code is None
        assert card.collector_number is None
        assert card.quantity == 1
        assert card.card_id is None
        assert card.in_collection is False
        assert card.owned_quantity == 0
        assert card.collection_entry_id is None
        assert card.image_url is None
        assert card.latest_price is None

    def test_full_values(self):
        card = DeckCardDetail(
            id=42,
            name_en="Counterspell",
            set_code="2ed",
            collector_number="55",
            quantity=4,
            card_id=100,
            in_collection=True,
            owned_quantity=3,
            collection_entry_id=200,
            image_url="https://example.com/img.png",
            latest_price=15.50,
        )
        assert card.card_id == 100
        assert card.in_collection is True
        assert card.owned_quantity == 3
        assert card.collection_entry_id == 200
        assert card.latest_price == 15.50

    def test_not_in_collection(self):
        card = DeckCardDetail(
            id=5,
            name_en="Force of Will",
            in_collection=False,
            owned_quantity=0,
        )
        assert card.in_collection is False
        assert card.owned_quantity == 0
        assert card.collection_entry_id is None
