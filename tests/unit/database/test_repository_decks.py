"""Tests for deck-related Repository methods."""

from __future__ import annotations

import pytest

from src.database.models import CardRow, UserCollectionRow
from src.database.repository import Repository


@pytest.fixture
def repo(tmp_path):
    db_path = tmp_path / "test.db"
    return Repository(f"sqlite:///{db_path}")


class TestCreateDeck:
    def test_creates_deck(self, repo):
        deck = repo.create_deck("user1", "My Deck")
        assert deck.id is not None
        assert deck.user_id == "user1"
        assert deck.name == "My Deck"
        assert deck.description is None

    def test_creates_deck_with_description(self, repo):
        deck = repo.create_deck("user1", "Burn", description="Fast red deck")
        assert deck.description == "Fast red deck"

    def test_multiple_decks(self, repo):
        d1 = repo.create_deck("user1", "Deck A")
        d2 = repo.create_deck("user1", "Deck B")
        assert d1.id != d2.id


class TestAddDeckCards:
    def test_add_cards(self, repo):
        deck = repo.create_deck("user1", "Test")
        count = repo.add_deck_cards(
            deck.id,
            [
                {
                    "name_en": "Lightning Bolt",
                    "set_code": "lea",
                    "collector_number": "161",
                    "quantity": 4,
                },
                {"name_en": "Mountain", "quantity": 20},
            ],
        )
        assert count == 2

    def test_add_empty_list(self, repo):
        deck = repo.create_deck("user1", "Empty")
        count = repo.add_deck_cards(deck.id, [])
        assert count == 0

    def test_card_fields_stored(self, repo):
        deck = repo.create_deck("user1", "Test")
        repo.add_deck_cards(
            deck.id,
            [
                {
                    "name_en": "Bolt",
                    "set_code": "lea",
                    "collector_number": "161",
                    "quantity": 4,
                    "card_id": 42,
                }
            ],
        )
        cards = repo.get_deck_cards(deck.id)
        assert len(cards) == 1
        c = cards[0]
        assert c.name_en == "Bolt"
        assert c.set_code == "lea"
        assert c.collector_number == "161"
        assert c.quantity == 4
        assert c.card_id == 42


class TestGetDeck:
    def test_existing(self, repo):
        created = repo.create_deck("user1", "Test")
        found = repo.get_deck(created.id)
        assert found is not None
        assert found.name == "Test"

    def test_not_found(self, repo):
        assert repo.get_deck(999) is None


class TestListDecks:
    def test_lists_user_decks(self, repo):
        repo.create_deck("user1", "A")
        repo.create_deck("user1", "B")
        repo.create_deck("user2", "C")
        decks = repo.list_decks("user1")
        assert len(decks) == 2
        names = [d.name for d in decks]
        assert "A" in names
        assert "B" in names

    def test_empty(self, repo):
        assert repo.list_decks("nobody") == []

    def test_ordered_by_created_desc(self, repo):
        repo.create_deck("user1", "First")
        repo.create_deck("user1", "Second")
        decks = repo.list_decks("user1")
        # Most recent first
        assert decks[0].name == "Second"
        assert decks[1].name == "First"


class TestDeleteDeck:
    def test_deletes_deck_and_cards(self, repo):
        deck = repo.create_deck("user1", "To Delete")
        repo.add_deck_cards(deck.id, [{"name_en": "Bolt", "quantity": 4}])
        result = repo.delete_deck(deck.id, "user1")
        assert result is True
        assert repo.get_deck(deck.id) is None
        assert repo.get_deck_cards(deck.id) == []

    def test_wrong_user(self, repo):
        deck = repo.create_deck("user1", "Mine")
        result = repo.delete_deck(deck.id, "user2")
        assert result is False
        assert repo.get_deck(deck.id) is not None

    def test_not_found(self, repo):
        result = repo.delete_deck(999, "user1")
        assert result is False


class TestGetDeckCards:
    def test_returns_cards(self, repo):
        deck = repo.create_deck("user1", "Test")
        repo.add_deck_cards(
            deck.id,
            [
                {"name_en": "A", "quantity": 1},
                {"name_en": "B", "quantity": 2},
            ],
        )
        cards = repo.get_deck_cards(deck.id)
        assert len(cards) == 2

    def test_empty_deck(self, repo):
        deck = repo.create_deck("user1", "Empty")
        assert repo.get_deck_cards(deck.id) == []


class TestGetDeckCardsWithOwnership:
    def _setup_collection(self, repo, user_id="user1"):
        """Set up a user collection for testing."""
        from sqlalchemy.orm import Session

        with Session(repo.engine) as session:
            # Create a canonical card
            card = CardRow(
                game="magic",
                name_en="Lightning Bolt",
                set_code="lea",
                collector_number="161",
            )
            session.add(card)
            session.commit()
            session.refresh(card)
            card_id = card.id

            # Add to user collection
            uc = UserCollectionRow(
                user_id=user_id,
                card_id=card_id,
                set_code="lea",
                collector_number="161",
                name_en="Lightning Bolt",
                quantity=3,
            )
            session.add(uc)
            session.commit()
            session.refresh(uc)
            return card_id, uc.id

    def test_match_by_card_id(self, repo):
        card_id, uc_id = self._setup_collection(repo)
        deck = repo.create_deck("user1", "Test")
        repo.add_deck_cards(deck.id, [{"name_en": "Lightning Bolt", "card_id": card_id}])

        results = repo.get_deck_cards_with_ownership(deck.id, "user1")
        assert len(results) == 1
        assert results[0]["in_collection"] is True
        assert results[0]["owned_quantity"] == 3
        assert results[0]["collection_entry_id"] == uc_id

    def test_match_by_set_code_number(self, repo):
        self._setup_collection(repo)
        deck = repo.create_deck("user1", "Test")
        repo.add_deck_cards(
            deck.id,
            [{"name_en": "Lightning Bolt", "set_code": "lea", "collector_number": "161"}],
        )

        results = repo.get_deck_cards_with_ownership(deck.id, "user1")
        assert results[0]["in_collection"] is True

    def test_match_by_name(self, repo):
        self._setup_collection(repo)
        deck = repo.create_deck("user1", "Test")
        repo.add_deck_cards(deck.id, [{"name_en": "Lightning Bolt"}])

        results = repo.get_deck_cards_with_ownership(deck.id, "user1")
        assert results[0]["in_collection"] is True

    def test_name_match_case_insensitive(self, repo):
        self._setup_collection(repo)
        deck = repo.create_deck("user1", "Test")
        repo.add_deck_cards(deck.id, [{"name_en": "lightning bolt"}])

        results = repo.get_deck_cards_with_ownership(deck.id, "user1")
        assert results[0]["in_collection"] is True

    def test_no_match(self, repo):
        self._setup_collection(repo)
        deck = repo.create_deck("user1", "Test")
        repo.add_deck_cards(deck.id, [{"name_en": "Force of Will"}])

        results = repo.get_deck_cards_with_ownership(deck.id, "user1")
        assert results[0]["in_collection"] is False
        assert results[0]["owned_quantity"] == 0
        assert results[0]["collection_entry_id"] is None

    def test_ambiguous_name_no_match(self, repo):
        """When multiple collection entries have the same name, no match."""
        from sqlalchemy.orm import Session

        with Session(repo.engine) as session:
            uc1 = UserCollectionRow(
                user_id="user1",
                set_code="lea",
                collector_number="161",
                name_en="Island",
                quantity=4,
            )
            uc2 = UserCollectionRow(
                user_id="user1",
                set_code="2ed",
                collector_number="100",
                name_en="Island",
                quantity=4,
            )
            session.add_all([uc1, uc2])
            session.commit()

        deck = repo.create_deck("user1", "Test")
        repo.add_deck_cards(deck.id, [{"name_en": "Island"}])

        results = repo.get_deck_cards_with_ownership(deck.id, "user1")
        # Ambiguous name → no match
        assert results[0]["in_collection"] is False

    def test_different_user_no_match(self, repo):
        self._setup_collection(repo, user_id="user1")
        deck = repo.create_deck("user2", "Test")
        repo.add_deck_cards(deck.id, [{"name_en": "Lightning Bolt"}])

        results = repo.get_deck_cards_with_ownership(deck.id, "user2")
        assert results[0]["in_collection"] is False


class TestGetDeckSummary:
    def test_summary(self, repo):
        from sqlalchemy.orm import Session

        with Session(repo.engine) as session:
            uc = UserCollectionRow(
                user_id="user1",
                set_code="lea",
                collector_number="161",
                name_en="Lightning Bolt",
                quantity=4,
            )
            session.add(uc)
            session.commit()

        deck = repo.create_deck("user1", "Test")
        repo.add_deck_cards(
            deck.id,
            [
                {"name_en": "Lightning Bolt", "quantity": 4},
                {"name_en": "Force of Will", "quantity": 2},
            ],
        )

        summary = repo.get_deck_summary(deck.id, "user1")
        assert summary["total_cards"] == 6
        assert summary["unique_cards"] == 2
        assert summary["owned_cards"] == 1
        assert summary["ownership_pct"] == 50.0

    def test_empty_deck_summary(self, repo):
        deck = repo.create_deck("user1", "Empty")
        summary = repo.get_deck_summary(deck.id, "user1")
        assert summary["total_cards"] == 0
        assert summary["unique_cards"] == 0
        assert summary["owned_cards"] == 0
        assert summary["ownership_pct"] == 0.0


class TestLinkDeckCard:
    def test_links_card(self, repo):
        deck = repo.create_deck("user1", "Test")
        repo.add_deck_cards(deck.id, [{"name_en": "Bolt"}])
        cards = repo.get_deck_cards(deck.id)
        assert cards[0].card_id is None

        repo.link_deck_card(cards[0].id, 42)
        cards = repo.get_deck_cards(deck.id)
        assert cards[0].card_id == 42
