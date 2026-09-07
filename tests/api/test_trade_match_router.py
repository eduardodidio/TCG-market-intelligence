"""Tests for the trade match API router (F110-T03/T04)."""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.api.routers.trade_match import router
from src.database.models import (
    CardRow,
    SharedCollectionRow,
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
    db_path = tmp_path / "test_trade_match.db"
    return Repository(db_url=f"sqlite:///{db_path}")


@pytest.fixture()
def user(repo):
    u = _make_user()
    repo.create_user(email=u.email, display_name=u.display_name)
    return u


@pytest.fixture()
def test_app(repo, user):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: user
    return app


@pytest.fixture()
def client(test_app):
    return TestClient(test_app)


@pytest.fixture()
def card_bolt(repo):
    with Session(repo.engine) as session:
        card = CardRow(
            game="magic",
            name_en="Lightning Bolt",
            set_code="2ed",
            collector_number="157",
            image_uri="https://example.com/bolt.jpg",
        )
        session.add(card)
        session.commit()
        session.refresh(card)
        return card.id


@pytest.fixture()
def card_counter(repo):
    with Session(repo.engine) as session:
        card = CardRow(
            game="magic",
            name_en="Counterspell",
            set_code="2ed",
            collector_number="55",
        )
        session.add(card)
        session.commit()
        session.refresh(card)
        return card.id


@pytest.fixture()
def partner_user(repo):
    """Create a second user with shared collection."""
    partner = repo.create_user(email="partner@example.com", display_name="Partner")
    with Session(repo.engine) as session:
        shared = SharedCollectionRow(
            user_id=partner.id,
            is_shared=1,
            share_code="PARTNER123",
            shared_at=datetime.now(),
        )
        session.add(shared)
        session.commit()
    return partner


class TestDuplicatesEndpoint:
    def test_no_duplicates(self, client):
        resp = client.get("/api/v1/trade/duplicates")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_has_duplicates(self, client, repo, user, card_bolt):
        with Session(repo.engine) as session:
            session.add(
                UserCollectionRow(
                    user_id=str(user.id),
                    set_code="2ed",
                    collector_number="157",
                    quantity=3,
                    name_en="Lightning Bolt",
                    card_id=card_bolt,
                )
            )
            session.commit()
        resp = client.get("/api/v1/trade/duplicates")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["card_id"] == card_bolt
        assert data[0]["quantity"] == 3
        assert data[0]["surplus"] == 2

    def test_null_card_id_excluded(self, client, repo, user):
        with Session(repo.engine) as session:
            session.add(
                UserCollectionRow(
                    user_id=str(user.id),
                    set_code="2ed",
                    collector_number="157",
                    quantity=5,
                    name_en="Lightning Bolt",
                    card_id=None,
                )
            )
            session.commit()
        resp = client.get("/api/v1/trade/duplicates")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_pagination(self, client, repo, user, card_bolt, card_counter):
        with Session(repo.engine) as session:
            session.add(
                UserCollectionRow(
                    user_id=str(user.id),
                    set_code="2ed",
                    collector_number="157",
                    quantity=3,
                    name_en="Lightning Bolt",
                    card_id=card_bolt,
                )
            )
            session.add(
                UserCollectionRow(
                    user_id=str(user.id),
                    set_code="2ed",
                    collector_number="55",
                    quantity=2,
                    name_en="Counterspell",
                    card_id=card_counter,
                )
            )
            session.commit()
        resp = client.get("/api/v1/trade/duplicates?limit=1")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1
        assert resp.json()["meta"]["total"] == 2


class TestDuplicatesCount:
    def test_count_zero(self, client):
        resp = client.get("/api/v1/trade/duplicates/count")
        assert resp.status_code == 200
        assert resp.json()["data"]["count"] == 0

    def test_count_with_duplicates(self, client, repo, user, card_bolt):
        with Session(repo.engine) as session:
            session.add(
                UserCollectionRow(
                    user_id=str(user.id),
                    set_code="2ed",
                    collector_number="157",
                    quantity=3,
                    name_en="Lightning Bolt",
                    card_id=card_bolt,
                )
            )
            session.commit()
        resp = client.get("/api/v1/trade/duplicates/count")
        assert resp.status_code == 200
        assert resp.json()["data"]["count"] == 1


class TestTradeMatches:
    def test_no_wishlist(self, client):
        resp = client.get("/api/v1/trade/matches")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_no_matching_partners(self, client, repo, user, card_bolt):
        # Add card to wishlist but no partner has it
        repo.add_wishlist_item(
            user_id=user.id,
            card_id=card_bolt,
            name_en="Lightning Bolt",
        )
        resp = client.get("/api/v1/trade/matches")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_matching_partner(self, client, repo, user, card_bolt, partner_user):
        # User wants Lightning Bolt
        repo.add_wishlist_item(
            user_id=user.id,
            card_id=card_bolt,
            name_en="Lightning Bolt",
        )
        # Partner has Lightning Bolt with quantity > 1
        with Session(repo.engine) as session:
            session.add(
                UserCollectionRow(
                    user_id=str(partner_user.id),
                    set_code="2ed",
                    collector_number="157",
                    quantity=3,
                    name_en="Lightning Bolt",
                    card_id=card_bolt,
                )
            )
            session.commit()

        resp = client.get("/api/v1/trade/matches")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["partner_name"] == "Partner"
        assert data[0]["share_code"] == "PARTNER123"
        assert data[0]["matching_card_count"] == 1
        assert data[0]["matched_cards"][0]["card_id"] == card_bolt

    def test_unshared_partner_excluded(self, client, repo, user, card_bolt):
        # Create partner WITHOUT shared collection
        partner = repo.create_user(email="private@example.com", display_name="Private")
        with Session(repo.engine) as session:
            session.add(
                SharedCollectionRow(
                    user_id=partner.id,
                    is_shared=0,
                    share_code="PRIVATE123",
                )
            )
            session.add(
                UserCollectionRow(
                    user_id=str(partner.id),
                    set_code="2ed",
                    collector_number="157",
                    quantity=3,
                    name_en="Lightning Bolt",
                    card_id=card_bolt,
                )
            )
            session.commit()

        repo.add_wishlist_item(
            user_id=user.id,
            card_id=card_bolt,
            name_en="Lightning Bolt",
        )
        resp = client.get("/api/v1/trade/matches")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_self_exclusion(self, client, repo, user, card_bolt):
        # User has own shared collection with duplicates
        with Session(repo.engine) as session:
            session.add(
                SharedCollectionRow(
                    user_id=user.id,
                    is_shared=1,
                    share_code="SELF123",
                    shared_at=datetime.now(),
                )
            )
            session.add(
                UserCollectionRow(
                    user_id=str(user.id),
                    set_code="2ed",
                    collector_number="157",
                    quantity=3,
                    name_en="Lightning Bolt",
                    card_id=card_bolt,
                )
            )
            session.commit()

        repo.add_wishlist_item(
            user_id=user.id,
            card_id=card_bolt,
            name_en="Lightning Bolt",
        )
        resp = client.get("/api/v1/trade/matches")
        assert resp.status_code == 200
        # Should NOT match own cards
        assert resp.json()["data"] == []


class TestReverseMatches:
    def test_no_duplicates(self, client):
        resp = client.get("/api/v1/trade/matches/reverse")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_reverse_match_found(self, client, repo, user, card_bolt, partner_user):
        # User has Lightning Bolt with quantity > 1
        with Session(repo.engine) as session:
            session.add(
                UserCollectionRow(
                    user_id=str(user.id),
                    set_code="2ed",
                    collector_number="157",
                    quantity=3,
                    name_en="Lightning Bolt",
                    card_id=card_bolt,
                )
            )
            session.commit()

        # Partner wants Lightning Bolt
        repo.add_wishlist_item(
            user_id=partner_user.id,
            card_id=card_bolt,
            name_en="Lightning Bolt",
        )

        resp = client.get("/api/v1/trade/matches/reverse")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["partner_name"] == "Partner"
        assert data[0]["share_code"] == "PARTNER123"

    def test_limit_parameter(self, client, repo, user, card_bolt, partner_user):
        with Session(repo.engine) as session:
            session.add(
                UserCollectionRow(
                    user_id=str(user.id),
                    set_code="2ed",
                    collector_number="157",
                    quantity=3,
                    name_en="Lightning Bolt",
                    card_id=card_bolt,
                )
            )
            session.commit()

        repo.add_wishlist_item(
            user_id=partner_user.id,
            card_id=card_bolt,
            name_en="Lightning Bolt",
        )

        resp = client.get("/api/v1/trade/matches/reverse?limit=1")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) <= 1
