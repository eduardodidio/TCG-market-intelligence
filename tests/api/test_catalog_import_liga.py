"""Tests for POST /catalog/import-liga endpoint (F148-T05)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.deps import get_credit_service, get_current_user, get_db
from src.api.routers.catalog import router
from src.database.models import (
    Base,
    CardRow,
    CreditBalanceRow,
    PriceUpdateRequestRow,
    UserRow,
)
from src.database.repository import Repository
from src.domain.models import User


@pytest.fixture()
def liga_repo():
    """In-memory DB with a catalog card and a user with credits."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        user = UserRow(
            id=1,
            email="test@test.com",
            display_name="Test",
            auth_provider="local",
            is_active=1,
            is_admin=0,
        )
        session.add(user)
        session.flush()

        session.add(CreditBalanceRow(user_id=1, balance=100))

        # Existing catalog card
        session.add(
            CardRow(
                id=10,
                game="magic",
                name_en="Lightning Bolt",
                set_code="m14",
                collector_number="1",
            )
        )
        session.add(
            CardRow(
                id=11,
                game="magic",
                name_en="Sol Ring",
                set_code="cmr",
                collector_number="1",
            )
        )
        session.commit()

    repo = Repository.__new__(Repository)
    repo.engine = engine
    return repo


def _make_user() -> User:
    return User(id=1, email="test@test.com", display_name="Test", is_admin=False)


@pytest.fixture()
def mock_credit_svc():
    from unittest.mock import MagicMock

    from src.credits.service import CreditService

    svc = MagicMock(spec=CreditService)
    svc.check_sufficient.return_value = True
    return svc


@pytest.fixture()
def client(liga_repo, mock_credit_svc):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: liga_repo
    app.dependency_overrides[get_current_user] = lambda: _make_user()
    app.dependency_overrides[get_credit_service] = lambda: mock_credit_svc
    return TestClient(app)


class TestImportLigaEndpoint:
    """POST /api/v1/catalog/import-liga tests."""

    def test_import_existing_card_queues_price(self, client, liga_repo):
        """Importing a card that exists returns queued with the card info."""
        resp = client.post(
            "/api/v1/catalog/import-liga",
            json={
                "url": "https://www.ligamagic.com.br/?view=cards/card&card=Lightning+Bolt&ed=m14"
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "queued"
        assert data["card_id"] == 10
        assert data["card_name"] == "Lightning Bolt"
        assert data["message"] == "Solicitacao enfileirada"

    def test_import_existing_card_creates_price_request(self, client, liga_repo):
        """Should create a price_update_requests row."""
        client.post(
            "/api/v1/catalog/import-liga",
            json={
                "url": "https://www.ligamagic.com.br/?view=cards/card&card=Lightning+Bolt&ed=m14"
            },
        )
        with Session(liga_repo.engine) as session:
            reqs = (
                session.execute(
                    select(PriceUpdateRequestRow).where(PriceUpdateRequestRow.card_id == 10)
                )
                .scalars()
                .all()
            )
        assert len(reqs) == 1
        assert reqs[0].status == "pending"

    def test_import_new_card_creates_card_and_queues(self, client, liga_repo):
        """Importing a card not in catalog creates it and queues price."""
        resp = client.post(
            "/api/v1/catalog/import-liga",
            json={"url": "https://www.ligamagic.com.br/?view=cards/card&card=Counterspell&ed=mh2"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "queued"
        assert data["card_name"] == "Counterspell"
        assert data["message"] == "Card adicionado e preco enfileirado"

        # Verify card was created in DB
        with Session(liga_repo.engine) as session:
            card = (
                session.execute(select(CardRow).where(CardRow.name_en == "Counterspell"))
                .scalars()
                .first()
            )
        assert card is not None
        assert card.set_code == "mh2"
        assert card.game == "magic"

    def test_import_new_card_without_set(self, client, liga_repo):
        """Importing without set code still works."""
        resp = client.post(
            "/api/v1/catalog/import-liga",
            json={"url": "https://www.ligamagic.com.br/?view=cards/card&card=Counterspell"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["card_name"] == "Counterspell"

    def test_import_invalid_url_returns_422(self, client):
        """Invalid URL returns 422."""
        resp = client.post(
            "/api/v1/catalog/import-liga",
            json={"url": "https://www.google.com/search?q=mtg"},
        )
        assert resp.status_code == 422

    def test_import_missing_card_param_returns_422(self, client):
        """URL without card param returns 422."""
        resp = client.post(
            "/api/v1/catalog/import-liga",
            json={"url": "https://www.ligamagic.com.br/?view=cards/card"},
        )
        assert resp.status_code == 422

    def test_import_deducts_credit(self, client, mock_credit_svc):
        """Should call deduct with cost=1."""
        client.post(
            "/api/v1/catalog/import-liga",
            json={"url": "https://www.ligamagic.com.br/?view=cards/card&card=Sol+Ring&ed=cmr"},
        )

        mock_credit_svc.deduct.assert_called_once_with(
            1,
            1,
            "import_liga",
            reference_id="11",
        )

    def test_import_insufficient_credits(self, liga_repo):
        """Should return 402 when credits are insufficient."""
        from unittest.mock import MagicMock

        from src.credits.service import CreditService

        svc = MagicMock(spec=CreditService)
        svc.check_sufficient.return_value = False

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_db] = lambda: liga_repo
        app.dependency_overrides[get_current_user] = lambda: _make_user()
        app.dependency_overrides[get_credit_service] = lambda: svc
        client = TestClient(app)

        resp = client.post(
            "/api/v1/catalog/import-liga",
            json={"url": "https://www.ligamagic.com.br/?view=cards/card&card=Sol+Ring"},
        )
        assert resp.status_code == 402

    def test_import_case_insensitive_match(self, client, liga_repo):
        """Card name matching should be case-insensitive."""
        resp = client.post(
            "/api/v1/catalog/import-liga",
            json={
                "url": "https://www.ligamagic.com.br/?view=cards/card&card=lightning+bolt&ed=m14"
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["card_id"] == 10
        assert data["message"] == "Solicitacao enfileirada"

    def test_import_duplicate_skips_credit_deduction(self, client, liga_repo, mock_credit_svc):
        """Importing the same card twice should skip credit deduction the second time."""
        # First import creates the price request
        resp1 = client.post(
            "/api/v1/catalog/import-liga",
            json={
                "url": "https://www.ligamagic.com.br/?view=cards/card&card=Lightning+Bolt&ed=m14"
            },
        )
        assert resp1.status_code == 200
        assert mock_credit_svc.deduct.call_count == 1

        # Second import should detect the pending request and skip
        resp2 = client.post(
            "/api/v1/catalog/import-liga",
            json={
                "url": "https://www.ligamagic.com.br/?view=cards/card&card=Lightning+Bolt&ed=m14"
            },
        )
        assert resp2.status_code == 200
        data = resp2.json()["data"]
        assert data["message"] == "Solicitacao ja enfileirada"
        # deduct should NOT have been called again
        assert mock_credit_svc.deduct.call_count == 1
