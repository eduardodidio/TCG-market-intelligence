"""Tests for wishlist hardening + collection duplicates detection (F213-T08)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.api.routers.collection import router as collection_router
from src.api.routers.wishlist import MAX_WISHLIST_ITEMS
from src.api.routers.wishlist import router as wishlist_router
from src.database.models import (
    CardRow,
    DeckCardRow,
    DeckRow,
    PriceObservationRow,
    SourceCardRow,
    UserCollectionRow,
)
from src.database.repository import Repository
from src.domain.models import User


def _make_user(user_id: int = 1) -> User:
    return User(
        id=user_id,
        email="test@example.com",
        display_name="Test User",
        auth_provider="email",
        is_active=True,
        is_admin=False,
    )


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_wl_dup.db"
    return Repository(db_url=f"sqlite:///{db_path}")


@pytest.fixture()
def user():
    return _make_user()


@pytest.fixture()
def test_app(repo, user):
    app = FastAPI()
    app.include_router(wishlist_router, prefix="/api/v1")
    app.include_router(collection_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: user
    repo.create_user(email=user.email, display_name=user.display_name)
    return app


@pytest.fixture()
def client(test_app):
    return TestClient(test_app)


@pytest.fixture()
def card_id(repo):
    with Session(repo.engine) as session:
        card = CardRow(
            game="magic",
            name_en="Lightning Bolt",
            name_pt="Raio",
            set_code="2ed",
            collector_number="157",
            image_uri="https://example.com/bolt.jpg",
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


@pytest.fixture()
def card_id_3(repo):
    with Session(repo.engine) as session:
        card = CardRow(
            game="magic",
            name_en="Sol Ring",
            name_pt="Anel Solar",
            set_code="cmd",
            collector_number="261",
        )
        session.add(card)
        session.commit()
        session.refresh(card)
        return card.id


# ── Wishlist CRUD Tests ──────────────────────────────────────


class TestWishlistCrud:
    def test_add_and_list(self, client, card_id):
        resp = client.post("/api/v1/wishlist", json={"card_id": card_id})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["card_id"] == card_id
        assert data["name_en"] == "Lightning Bolt"
        assert data["is_acquired"] is False
        assert data["any_version"] is False

        resp = client.get("/api/v1/wishlist")
        assert resp.status_code == 200
        items = resp.json()["data"]
        assert len(items) == 1
        assert items[0]["card_id"] == card_id

    def test_add_with_any_version(self, client, card_id):
        resp = client.post(
            "/api/v1/wishlist",
            json={"card_id": card_id, "any_version": True},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["any_version"] is True

    def test_remove(self, client, card_id):
        client.post("/api/v1/wishlist", json={"card_id": card_id})
        resp = client.delete(f"/api/v1/wishlist/{card_id}")
        assert resp.status_code == 204

        resp = client.get("/api/v1/wishlist")
        assert resp.json()["data"] == []

    def test_add_nonexistent_card_404(self, client):
        resp = client.post("/api/v1/wishlist", json={"card_id": 99999})
        assert resp.status_code == 404

    def test_add_duplicate_409(self, client, card_id):
        client.post("/api/v1/wishlist", json={"card_id": card_id})
        resp = client.post("/api/v1/wishlist", json={"card_id": card_id})
        assert resp.status_code == 409


# ── Wishlist 200-Item Limit ──────────────────────────────────


class TestWishlistLimit:
    def test_max_items_returns_400(self, repo, client, user):
        """Adding more than MAX_WISHLIST_ITEMS returns 400."""
        # Insert MAX_WISHLIST_ITEMS cards directly in DB to avoid slowness
        with Session(repo.engine) as session:
            for i in range(MAX_WISHLIST_ITEMS):
                card = CardRow(
                    game="magic",
                    name_en=f"Card {i}",
                    set_code="tst",
                    collector_number=str(i),
                )
                session.add(card)
            session.commit()

            # Fetch all card IDs
            all_cards = session.query(CardRow).filter(CardRow.set_code == "tst").all()
            card_ids = [c.id for c in all_cards]

        # Add MAX_WISHLIST_ITEMS items to wishlist via repo
        for cid in card_ids[:MAX_WISHLIST_ITEMS]:
            repo.add_wishlist_item(
                user_id=user.id,
                card_id=cid,
                name_en=f"Card {cid}",
            )

        # Create one more card for the overflow attempt
        with Session(repo.engine) as session:
            overflow_card = CardRow(
                game="magic",
                name_en="Overflow Card",
                set_code="tst",
                collector_number="overflow",
            )
            session.add(overflow_card)
            session.commit()
            session.refresh(overflow_card)
            overflow_id = overflow_card.id

        resp = client.post("/api/v1/wishlist", json={"card_id": overflow_id})
        assert resp.status_code == 400
        assert "Maximum" in resp.json()["detail"]


# ── Wishlist current_price ───────────────────────────────────


class TestWishlistCurrentPrice:
    def test_current_price_in_list(self, repo, client, card_id):
        """List endpoint includes current_price from price observations."""
        # Add card to wishlist
        client.post("/api/v1/wishlist", json={"card_id": card_id})

        # Create a source_card + price observation for the card
        with Session(repo.engine) as session:
            sc = SourceCardRow(
                source="myp",
                external_id=f"myp_{card_id}",
                card_id=card_id,
                url="https://mypcards.com/test",
                name_en="Lightning Bolt",
                set_code="2ed",
                collector_number="157",
            )
            session.add(sc)
            session.flush()

            obs = PriceObservationRow(
                source="myp",
                external_id=f"myp_{card_id}",
                observed_at=date.today(),
                median_price=Decimal("12.50"),
                currency="BRL",
            )
            session.add(obs)
            session.commit()

        resp = client.get("/api/v1/wishlist")
        assert resp.status_code == 200
        items = resp.json()["data"]
        assert len(items) == 1
        assert items[0]["current_price"] == 12.50

    def test_current_price_null_when_no_observation(self, client, card_id):
        """current_price is null when no price observation exists."""
        client.post("/api/v1/wishlist", json={"card_id": card_id})

        resp = client.get("/api/v1/wishlist")
        items = resp.json()["data"]
        assert items[0]["current_price"] is None


# ── Collection Duplicates Detection ──────────────────────────


class TestCollectionDuplicates:
    def _add_collection_entry(self, repo, user, card_id, quantity, name_en="Card"):
        with Session(repo.engine) as session:
            entry = UserCollectionRow(
                user_id=str(user.id),
                card_id=card_id,
                set_code="2ed",
                collector_number="1",
                quantity=quantity,
                name_en=name_en,
            )
            session.add(entry)
            session.commit()

    def _add_deck_with_card(self, repo, user, card_id, qty, deck_name="Test Deck"):
        with Session(repo.engine) as session:
            deck = DeckRow(
                user_id=str(user.id),
                name=deck_name,
            )
            session.add(deck)
            session.flush()

            dc = DeckCardRow(
                deck_id=deck.id,
                name_en="Card",
                card_id=card_id,
                quantity=qty,
            )
            session.add(dc)
            session.commit()
            return deck.id

    def _add_price(self, repo, card_id, price):
        with Session(repo.engine) as session:
            sc = SourceCardRow(
                source="myp",
                external_id=f"myp_{card_id}",
                card_id=card_id,
                url="https://mypcards.com/test",
                name_en="Card",
            )
            session.add(sc)
            session.flush()
            obs = PriceObservationRow(
                source="myp",
                external_id=f"myp_{card_id}",
                observed_at=date.today(),
                median_price=Decimal(str(price)),
                currency="BRL",
            )
            session.add(obs)
            session.commit()

    def test_duplicates_basic(self, repo, client, user, card_id):
        """3 owned, 1 in deck = surplus 2."""
        self._add_collection_entry(repo, user, card_id, 3, "Lightning Bolt")
        self._add_deck_with_card(repo, user, card_id, 1)

        resp = client.get("/api/v1/collection/duplicates")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["card_id"] == card_id
        assert data[0]["owned_qty"] == 3
        assert data[0]["needed_qty"] == 1
        assert data[0]["surplus"] == 2

    def test_duplicates_with_higher_deck_usage(self, repo, client, user, card_id):
        """3 owned, 2 in decks = surplus 1."""
        self._add_collection_entry(repo, user, card_id, 3, "Lightning Bolt")
        self._add_deck_with_card(repo, user, card_id, 2)

        resp = client.get("/api/v1/collection/duplicates")
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["surplus"] == 1
        assert data[0]["needed_qty"] == 2

    def test_duplicates_empty_no_surplus(self, repo, client, user, card_id):
        """1 owned, 1 needed = no surplus."""
        self._add_collection_entry(repo, user, card_id, 1, "Lightning Bolt")

        resp = client.get("/api/v1/collection/duplicates")
        data = resp.json()["data"]
        assert len(data) == 0

    def test_duplicates_empty_exact_match(self, repo, client, user, card_id):
        """2 owned, 2 in deck = no surplus."""
        self._add_collection_entry(repo, user, card_id, 2, "Lightning Bolt")
        self._add_deck_with_card(repo, user, card_id, 2)

        resp = client.get("/api/v1/collection/duplicates")
        data = resp.json()["data"]
        assert len(data) == 0

    def test_duplicates_no_deck_usage_still_surplus(self, repo, client, user, card_id):
        """3 owned, 0 in decks = needed 1, surplus 2."""
        self._add_collection_entry(repo, user, card_id, 3, "Lightning Bolt")

        resp = client.get("/api/v1/collection/duplicates")
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["needed_qty"] == 1
        assert data[0]["surplus"] == 2

    def test_duplicates_sorted_by_value(self, repo, client, user, card_id, card_id_2):
        """Higher estimated_value card appears first."""
        # Card 1: surplus 2, price 5.00 => value 10.00
        self._add_collection_entry(repo, user, card_id, 3, "Lightning Bolt")
        self._add_price(repo, card_id, 5.00)

        # Card 2: surplus 1, price 25.00 => value 25.00
        self._add_collection_entry(repo, user, card_id_2, 2, "Counterspell")
        self._add_price(repo, card_id_2, 25.00)

        resp = client.get("/api/v1/collection/duplicates")
        data = resp.json()["data"]
        assert len(data) == 2
        # Counterspell (value 25) should come before Lightning Bolt (value 10)
        assert data[0]["card_id"] == card_id_2
        assert data[0]["estimated_value"] == 25.00
        assert data[1]["card_id"] == card_id
        assert data[1]["estimated_value"] == 10.00

    def test_duplicates_across_multiple_decks(self, repo, client, user, card_id):
        """Card used in 2 decks: 1 + 1 = 2 needed, 4 owned = surplus 2."""
        self._add_collection_entry(repo, user, card_id, 4, "Lightning Bolt")
        self._add_deck_with_card(repo, user, card_id, 1, "Deck A")
        self._add_deck_with_card(repo, user, card_id, 1, "Deck B")

        resp = client.get("/api/v1/collection/duplicates")
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["needed_qty"] == 2
        assert data[0]["surplus"] == 2

    def test_duplicates_includes_total(self, repo, client, user, card_id, card_id_2):
        """Response includes total count in meta."""
        self._add_collection_entry(repo, user, card_id, 3, "Lightning Bolt")
        self._add_collection_entry(repo, user, card_id_2, 2, "Counterspell")

        resp = client.get("/api/v1/collection/duplicates")
        assert resp.json()["meta"]["total"] == 2
