"""Tests for BRL currency conversion in batch parse/add (F171-T09)."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.deps import get_currency_converter_dep, get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.database.models import Base, UserCollectionRow

_TEST_USER_ID = "test-user-42"


def _stub_currency_converter_dep(rate: Decimal | None = Decimal("5.00")):
    """Build a dependency override for get_currency_converter_dep."""

    def _dep():
        converter = MagicMock()
        converter.get_display_rate.return_value = rate
        yield converter

    return _dep


def _create_app(
    repo_override=None,
    rate: Decimal | None = Decimal("5.00"),
    user_id: str = _TEST_USER_ID,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    if repo_override is not None:
        app.dependency_overrides[get_db] = lambda: repo_override

    app.dependency_overrides[require_auth_or_api_key] = lambda: user_id
    app.dependency_overrides[get_currency_converter_dep] = _stub_currency_converter_dep(rate)
    return app


def _create_test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


class TestBatchParseCurrency:
    """POST /collection/batch/parse surfaces detected price/currency."""

    def test_parse_usd_price(self) -> None:
        app = _create_app()
        client = TestClient(app)

        resp = client.post(
            "/api/v1/collection/batch/parse",
            json={"text": "Sol Ring US$3.10"},
        )
        assert resp.status_code == 200
        entries = resp.json()["data"]["entries"]
        assert len(entries) == 1
        assert entries[0]["price"] == "3.10"
        assert entries[0]["price_currency"] == "USD"

    def test_parse_no_price(self) -> None:
        app = _create_app()
        client = TestClient(app)

        resp = client.post(
            "/api/v1/collection/batch/parse",
            json={"text": "Sol Ring"},
        )
        assert resp.status_code == 200
        entries = resp.json()["data"]["entries"]
        assert entries[0]["price"] is None
        assert entries[0]["price_currency"] is None


class TestBatchAddCurrency:
    """POST /collection/batch converts acquisition_price to BRL."""

    def test_usd_price_converted_to_brl(self) -> None:
        engine = _create_test_db()
        repo = MagicMock()
        repo.engine = engine

        app = _create_app(repo_override=repo, rate=Decimal("5.00"))
        client = TestClient(app)

        resp = client.post(
            "/api/v1/collection/batch",
            json={
                "entries": [
                    {
                        "name_en": "Sol Ring",
                        "acquisition_price": "3.10",
                        "price_currency": "USD",
                    }
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["added"] == 1
        assert data["warnings"] == []

        with Session(engine) as session:
            row = session.query(UserCollectionRow).first()
            assert row.acquisition_price == Decimal("15.50")

    def test_brl_price_stored_unchanged(self) -> None:
        engine = _create_test_db()
        repo = MagicMock()
        repo.engine = engine

        app = _create_app(repo_override=repo, rate=Decimal("5.00"))
        client = TestClient(app)

        resp = client.post(
            "/api/v1/collection/batch",
            json={
                "entries": [
                    {
                        "name_en": "Lightning Bolt",
                        "acquisition_price": "12.50",
                        "price_currency": "BRL",
                    }
                ]
            },
        )
        assert resp.status_code == 200

        with Session(engine) as session:
            row = session.query(UserCollectionRow).first()
            assert row.acquisition_price == Decimal("12.50")

    def test_none_currency_treated_as_brl(self) -> None:
        engine = _create_test_db()
        repo = MagicMock()
        repo.engine = engine

        app = _create_app(repo_override=repo, rate=Decimal("5.00"))
        client = TestClient(app)

        resp = client.post(
            "/api/v1/collection/batch",
            json={
                "entries": [
                    {
                        "name_en": "Counterspell",
                        "acquisition_price": "7.00",
                    }
                ]
            },
        )
        assert resp.status_code == 200

        with Session(engine) as session:
            row = session.query(UserCollectionRow).first()
            assert row.acquisition_price == Decimal("7.00")

    def test_no_rate_adds_warning_and_keeps_row(self) -> None:
        engine = _create_test_db()
        repo = MagicMock()
        repo.engine = engine

        app = _create_app(repo_override=repo, rate=None)
        client = TestClient(app)

        resp = client.post(
            "/api/v1/collection/batch",
            json={
                "entries": [
                    {
                        "name_en": "Sol Ring",
                        "acquisition_price": "3.10",
                        "price_currency": "USD",
                    }
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["added"] == 1
        assert len(data["warnings"]) == 1
        assert "no_rate" in data["warnings"][0]

        with Session(engine) as session:
            row = session.query(UserCollectionRow).first()
            assert row.acquisition_price is None

    def test_zero_price_passes(self) -> None:
        engine = _create_test_db()
        repo = MagicMock()
        repo.engine = engine

        app = _create_app(repo_override=repo, rate=Decimal("5.00"))
        client = TestClient(app)

        resp = client.post(
            "/api/v1/collection/batch",
            json={
                "entries": [
                    {
                        "name_en": "Free Card",
                        "acquisition_price": "0",
                        "price_currency": "BRL",
                    }
                ]
            },
        )
        assert resp.status_code == 200

        with Session(engine) as session:
            row = session.query(UserCollectionRow).first()
            assert row.acquisition_price == Decimal("0.00")

    def test_negative_price_rejected(self) -> None:
        app = _create_app()
        client = TestClient(app)

        resp = client.post(
            "/api/v1/collection/batch",
            json={
                "entries": [
                    {
                        "name_en": "Sol Ring",
                        "acquisition_price": "-1.00",
                        "price_currency": "USD",
                    }
                ]
            },
        )
        assert resp.status_code == 422

    def test_unsupported_currency_rejected(self) -> None:
        app = _create_app()
        client = TestClient(app)

        resp = client.post(
            "/api/v1/collection/batch",
            json={
                "entries": [
                    {
                        "name_en": "Sol Ring",
                        "acquisition_price": "1.00",
                        "price_currency": "EUR",
                    }
                ]
            },
        )
        assert resp.status_code == 422

    def test_old_payload_without_price_fields_still_works(self) -> None:
        engine = _create_test_db()
        repo = MagicMock()
        repo.engine = engine

        app = _create_app(repo_override=repo, rate=Decimal("5.00"))
        client = TestClient(app)

        resp = client.post(
            "/api/v1/collection/batch",
            json={"entries": [{"name_en": "Lightning Bolt"}]},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["added"] == 1
        assert data["warnings"] == []

        with Session(engine) as session:
            row = session.query(UserCollectionRow).first()
            assert row.acquisition_price is None

    def test_500_entries_with_prices(self) -> None:
        engine = _create_test_db()
        repo = MagicMock()
        repo.engine = engine

        app = _create_app(repo_override=repo, rate=Decimal("5.00"))
        client = TestClient(app)

        entries = [
            {"name_en": f"Card {i}", "acquisition_price": "1.00", "price_currency": "USD"}
            for i in range(500)
        ]
        resp = client.post(
            "/api/v1/collection/batch",
            json={"entries": entries},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["added"] == 500

        with Session(engine) as session:
            rows = session.query(UserCollectionRow).all()
            assert len(rows) == 500
            assert all(r.acquisition_price == Decimal("5.00") for r in rows)
