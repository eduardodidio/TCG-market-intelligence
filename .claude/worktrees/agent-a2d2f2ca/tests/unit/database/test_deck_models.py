"""Tests for DeckRow and DeckCardRow database models."""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from src.database.models import Base, DeckCardRow, DeckRow


@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "test.db"
    eng = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(eng)
    return eng


class TestDeckRow:
    def test_create_deck(self, engine):
        with Session(engine) as session:
            deck = DeckRow(user_id="user1", name="My Deck")
            session.add(deck)
            session.commit()
            session.refresh(deck)

            assert deck.id is not None
            assert deck.user_id == "user1"
            assert deck.name == "My Deck"
            assert deck.description is None
            assert isinstance(deck.created_at, datetime)
            assert isinstance(deck.updated_at, datetime)

    def test_create_deck_with_description(self, engine):
        with Session(engine) as session:
            deck = DeckRow(
                user_id="user1",
                name="Burn Deck",
                description="A fast aggro deck",
            )
            session.add(deck)
            session.commit()
            session.refresh(deck)

            assert deck.description == "A fast aggro deck"

    def test_multiple_decks_same_user(self, engine):
        with Session(engine) as session:
            d1 = DeckRow(user_id="user1", name="Deck A")
            d2 = DeckRow(user_id="user1", name="Deck B")
            session.add_all([d1, d2])
            session.commit()

            rows = (
                session.execute(select(DeckRow).where(DeckRow.user_id == "user1")).scalars().all()
            )
            assert len(rows) == 2

    def test_different_users(self, engine):
        with Session(engine) as session:
            d1 = DeckRow(user_id="user1", name="Deck A")
            d2 = DeckRow(user_id="user2", name="Deck B")
            session.add_all([d1, d2])
            session.commit()

            rows = (
                session.execute(select(DeckRow).where(DeckRow.user_id == "user1")).scalars().all()
            )
            assert len(rows) == 1
            assert rows[0].name == "Deck A"


class TestDeckCardRow:
    def test_create_deck_card(self, engine):
        with Session(engine) as session:
            deck = DeckRow(user_id="user1", name="Test Deck")
            session.add(deck)
            session.commit()
            session.refresh(deck)

            card = DeckCardRow(
                deck_id=deck.id,
                name_en="Lightning Bolt",
                set_code="lea",
                collector_number="161",
                quantity=4,
            )
            session.add(card)
            session.commit()
            session.refresh(card)

            assert card.id is not None
            assert card.deck_id == deck.id
            assert card.name_en == "Lightning Bolt"
            assert card.set_code == "lea"
            assert card.collector_number == "161"
            assert card.quantity == 4
            assert card.card_id is None

    def test_deck_card_with_card_id(self, engine):
        with Session(engine) as session:
            deck = DeckRow(user_id="user1", name="Linked Deck")
            session.add(deck)
            session.commit()
            session.refresh(deck)

            card = DeckCardRow(
                deck_id=deck.id,
                name_en="Counterspell",
                card_id=42,
                quantity=2,
            )
            session.add(card)
            session.commit()
            session.refresh(card)

            assert card.card_id == 42

    def test_deck_card_minimal(self, engine):
        """Card with only required fields."""
        with Session(engine) as session:
            deck = DeckRow(user_id="user1", name="Minimal Deck")
            session.add(deck)
            session.commit()
            session.refresh(deck)

            card = DeckCardRow(deck_id=deck.id, name_en="Island")
            session.add(card)
            session.commit()
            session.refresh(card)

            assert card.set_code is None
            assert card.collector_number is None
            assert card.quantity == 1
            assert card.card_id is None

    def test_multiple_cards_same_deck(self, engine):
        with Session(engine) as session:
            deck = DeckRow(user_id="user1", name="Full Deck")
            session.add(deck)
            session.commit()
            session.refresh(deck)

            cards = [
                DeckCardRow(deck_id=deck.id, name_en="Lightning Bolt", quantity=4),
                DeckCardRow(deck_id=deck.id, name_en="Mountain", quantity=20),
                DeckCardRow(deck_id=deck.id, name_en="Goblin Guide", quantity=4),
            ]
            session.add_all(cards)
            session.commit()

            rows = (
                session.execute(select(DeckCardRow).where(DeckCardRow.deck_id == deck.id))
                .scalars()
                .all()
            )
            assert len(rows) == 3
