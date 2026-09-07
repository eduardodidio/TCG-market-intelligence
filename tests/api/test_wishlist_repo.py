"""Tests for wishlist repository methods (F110-T01)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from src.database.models import CardRow, UserCollectionRow, UserRow, WishlistRow
from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_wishlist.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


@pytest.fixture()
def user_id(repo):
    user = repo.create_user(email="test@example.com", display_name="Test User")
    return user.id


@pytest.fixture()
def card_id(repo):
    with Session(repo.engine) as session:
        card = CardRow(
            game="magic",
            name_en="Lightning Bolt",
            name_pt="Raio",
            set_code="2ed",
            collector_number="157",
        )
        session.add(card)
        session.commit()
        session.refresh(card)
        return card.id


@pytest.fixture()
def card_id_2(repo):
    with Session(repo.engine) as session:
        card = CardRow(
            game="magic",
            name_en="Counterspell",
            name_pt="Contrafeitico",
            set_code="2ed",
            collector_number="55",
        )
        session.add(card)
        session.commit()
        session.refresh(card)
        return card.id


class TestAddWishlistItem:
    def test_add_success(self, repo, user_id, card_id):
        row = repo.add_wishlist_item(
            user_id=user_id,
            card_id=card_id,
            name_en="Lightning Bolt",
            name_pt="Raio",
            set_code="2ed",
            collector_number="157",
        )
        assert row is not None
        assert row.user_id == user_id
        assert row.card_id == card_id
        assert row.name_en == "Lightning Bolt"
        assert row.is_acquired == 0

    def test_add_with_max_price(self, repo, user_id, card_id):
        row = repo.add_wishlist_item(
            user_id=user_id,
            card_id=card_id,
            name_en="Lightning Bolt",
            max_price=Decimal("10.50"),
        )
        assert row is not None
        assert float(row.max_price) == 10.50

    def test_add_with_notes(self, repo, user_id, card_id):
        row = repo.add_wishlist_item(
            user_id=user_id,
            card_id=card_id,
            name_en="Lightning Bolt",
            notes="Need for Commander deck",
        )
        assert row is not None
        assert row.notes == "Need for Commander deck"

    def test_add_duplicate_returns_none(self, repo, user_id, card_id):
        repo.add_wishlist_item(user_id=user_id, card_id=card_id, name_en="Lightning Bolt")
        result = repo.add_wishlist_item(user_id=user_id, card_id=card_id, name_en="Lightning Bolt")
        assert result is None


class TestRemoveWishlistItem:
    def test_remove_existing(self, repo, user_id, card_id):
        repo.add_wishlist_item(user_id=user_id, card_id=card_id, name_en="Lightning Bolt")
        assert repo.remove_wishlist_item(user_id, card_id) is True

    def test_remove_nonexistent(self, repo, user_id, card_id):
        assert repo.remove_wishlist_item(user_id, card_id) is False


class TestGetWishlist:
    def test_get_empty(self, repo, user_id):
        items, total = repo.get_wishlist(user_id)
        assert items == []
        assert total == 0

    def test_get_items(self, repo, user_id, card_id, card_id_2):
        repo.add_wishlist_item(user_id=user_id, card_id=card_id, name_en="Lightning Bolt")
        repo.add_wishlist_item(user_id=user_id, card_id=card_id_2, name_en="Counterspell")
        items, total = repo.get_wishlist(user_id)
        assert total == 2
        assert len(items) == 2

    def test_get_exclude_acquired(self, repo, user_id, card_id, card_id_2):
        repo.add_wishlist_item(user_id=user_id, card_id=card_id, name_en="Lightning Bolt")
        repo.add_wishlist_item(user_id=user_id, card_id=card_id_2, name_en="Counterspell")
        repo.mark_wishlist_acquired(user_id, card_id)
        items, total = repo.get_wishlist(user_id, include_acquired=False)
        assert total == 1
        assert items[0].name_en == "Counterspell"

    def test_get_with_search(self, repo, user_id, card_id, card_id_2):
        repo.add_wishlist_item(user_id=user_id, card_id=card_id, name_en="Lightning Bolt")
        repo.add_wishlist_item(user_id=user_id, card_id=card_id_2, name_en="Counterspell")
        items, total = repo.get_wishlist(user_id, search="bolt")
        assert total == 1
        assert items[0].name_en == "Lightning Bolt"

    def test_get_pagination(self, repo, user_id, card_id, card_id_2):
        repo.add_wishlist_item(user_id=user_id, card_id=card_id, name_en="Lightning Bolt")
        repo.add_wishlist_item(user_id=user_id, card_id=card_id_2, name_en="Counterspell")
        items, total = repo.get_wishlist(user_id, limit=1, offset=0)
        assert total == 2
        assert len(items) == 1


class TestMarkWishlistAcquired:
    def test_mark_acquired(self, repo, user_id, card_id):
        repo.add_wishlist_item(user_id=user_id, card_id=card_id, name_en="Lightning Bolt")
        assert repo.mark_wishlist_acquired(user_id, card_id) is True
        items, _ = repo.get_wishlist(user_id)
        assert items[0].is_acquired == 1
        assert items[0].acquired_at is not None

    def test_mark_nonexistent(self, repo, user_id, card_id):
        assert repo.mark_wishlist_acquired(user_id, card_id) is False


class TestIsInWishlist:
    def test_in_wishlist(self, repo, user_id, card_id):
        repo.add_wishlist_item(user_id=user_id, card_id=card_id, name_en="Lightning Bolt")
        assert repo.is_in_wishlist(user_id, card_id) is True

    def test_not_in_wishlist(self, repo, user_id, card_id):
        assert repo.is_in_wishlist(user_id, card_id) is False


class TestGetWishlistCardIds:
    def test_get_card_ids(self, repo, user_id, card_id, card_id_2):
        repo.add_wishlist_item(user_id=user_id, card_id=card_id, name_en="Lightning Bolt")
        repo.add_wishlist_item(user_id=user_id, card_id=card_id_2, name_en="Counterspell")
        ids = repo.get_wishlist_card_ids(user_id)
        assert ids == {card_id, card_id_2}

    def test_empty(self, repo, user_id):
        ids = repo.get_wishlist_card_ids(user_id)
        assert ids == set()


class TestCascadeDelete:
    def test_delete_card_removes_wishlist(self, repo, user_id, card_id):
        repo.add_wishlist_item(user_id=user_id, card_id=card_id, name_en="Lightning Bolt")
        with Session(repo.engine) as session:
            card = session.get(CardRow, card_id)
            session.delete(card)
            session.commit()
        items, total = repo.get_wishlist(user_id)
        assert total == 0

    def test_delete_user_removes_wishlist(self, repo, user_id, card_id):
        repo.add_wishlist_item(user_id=user_id, card_id=card_id, name_en="Lightning Bolt")
        with Session(repo.engine) as session:
            user = session.get(UserRow, user_id)
            session.delete(user)
            session.commit()
        with Session(repo.engine) as session:
            count = session.query(WishlistRow).count()
            assert count == 0


class TestGetUserDuplicates:
    def test_no_duplicates(self, repo, user_id, card_id):
        with Session(repo.engine) as session:
            entry = UserCollectionRow(
                user_id=str(user_id),
                set_code="2ed",
                collector_number="157",
                quantity=1,
                name_en="Lightning Bolt",
                card_id=card_id,
            )
            session.add(entry)
            session.commit()
        dupes, total = repo.get_user_duplicates(user_id)
        assert total == 0
        assert dupes == []

    def test_has_duplicates(self, repo, user_id, card_id):
        with Session(repo.engine) as session:
            entry = UserCollectionRow(
                user_id=str(user_id),
                set_code="2ed",
                collector_number="157",
                quantity=3,
                name_en="Lightning Bolt",
                card_id=card_id,
            )
            session.add(entry)
            session.commit()
        dupes, total = repo.get_user_duplicates(user_id)
        assert total == 1
        assert dupes[0]["card_id"] == card_id
        assert dupes[0]["quantity"] == 3
        assert dupes[0]["surplus"] == 2

    def test_null_card_id_excluded(self, repo, user_id):
        with Session(repo.engine) as session:
            entry = UserCollectionRow(
                user_id=str(user_id),
                set_code="2ed",
                collector_number="157",
                quantity=5,
                name_en="Lightning Bolt",
                card_id=None,
            )
            session.add(entry)
            session.commit()
        dupes, total = repo.get_user_duplicates(user_id)
        assert total == 0

    def test_pagination(self, repo, user_id, card_id, card_id_2):
        with Session(repo.engine) as session:
            session.add(
                UserCollectionRow(
                    user_id=str(user_id),
                    set_code="2ed",
                    collector_number="157",
                    quantity=3,
                    name_en="Lightning Bolt",
                    card_id=card_id,
                )
            )
            session.add(
                UserCollectionRow(
                    user_id=str(user_id),
                    set_code="2ed",
                    collector_number="55",
                    quantity=2,
                    name_en="Counterspell",
                    card_id=card_id_2,
                )
            )
            session.commit()
        dupes, total = repo.get_user_duplicates(user_id, limit=1)
        assert total == 2
        assert len(dupes) == 1


class TestGetUserDuplicateCardIds:
    def test_empty(self, repo, user_id):
        result = repo.get_user_duplicate_card_ids(user_id)
        assert result == {}

    def test_has_surplus(self, repo, user_id, card_id):
        with Session(repo.engine) as session:
            session.add(
                UserCollectionRow(
                    user_id=str(user_id),
                    set_code="2ed",
                    collector_number="157",
                    quantity=4,
                    name_en="Lightning Bolt",
                    card_id=card_id,
                )
            )
            session.commit()
        result = repo.get_user_duplicate_card_ids(user_id)
        assert result == {card_id: 3}
