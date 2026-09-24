"""Tests for `currency` + `dry_run` query params on POST /collection/import (F171-T10)."""

from __future__ import annotations

import io
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool

from src.api.deps import get_currency_converter_dep, get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.database.models import Base, UserCollectionRow

_TEST_USER_ID = "test-user-42"
_FIXTURES = Path(__file__).parent.parent / "fixtures" / "collection_import"


def _stub_currency_converter_dep(rate: Decimal | None = Decimal("5.40")):
    """Build a dependency override for get_currency_converter_dep."""

    def _dep():
        converter = MagicMock()
        converter.get_display_rate.return_value = rate
        yield converter

    return _dep


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


def _create_app(
    engine, rate: Decimal | None = Decimal("5.40"), user_id: str = _TEST_USER_ID
) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    repo = MagicMock()
    repo.engine = engine

    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: user_id
    app.dependency_overrides[get_currency_converter_dep] = _stub_currency_converter_dep(rate)
    return app


def _upload(client: TestClient, filename: str, params: dict | None = None):
    csv_bytes = (_FIXTURES / filename).read_bytes()
    return client.post(
        "/api/v1/collection/import",
        files={"file": (filename, io.BytesIO(csv_bytes), "text/csv")},
        params=params or {},
    )


class TestImportCurrencyDetectionAndConversion:
    def test_usd_symbol_file_converts_at_rate(self) -> None:
        engine = _create_test_db()
        app = _create_app(engine, rate=Decimal("5.40"))
        client = TestClient(app)

        resp = _upload(client, "generic_usd_symbol.csv")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["detected_currency"] == "USD"
        assert data["converted"] == 3
        assert data["exchange_rate"] == "5.40"

        from sqlalchemy.orm import Session

        with Session(engine) as session:
            rows = session.query(UserCollectionRow).order_by(UserCollectionRow.id).all()
            assert len(rows) == 3
            prices = {row.collector_number: row.acquisition_price for row in rows}
            assert prices["146"] == Decimal("2.00") * Decimal("5.40")
            assert prices["263"] == Decimal("0.50") * Decimal("5.40")
            assert prices["98"] == Decimal("1050.00") * Decimal("5.40")

    def test_currency_override_forces_brl(self) -> None:
        engine = _create_test_db()
        app = _create_app(engine, rate=Decimal("5.40"))
        client = TestClient(app)

        resp = _upload(client, "generic_usd_symbol.csv", params={"currency": "BRL"})
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["detected_currency"] == "BRL"
        assert data["converted"] == 0

        from sqlalchemy.orm import Session

        with Session(engine) as session:
            rows = session.query(UserCollectionRow).all()
            assert all(row.acquisition_price is not None for row in rows)
            prices = {row.collector_number: row.acquisition_price for row in rows}
            assert prices["146"] == Decimal("2.00")

    def test_dry_run_does_not_write_rows_or_schedule_canonize(self) -> None:
        engine = _create_test_db()
        app = _create_app(engine, rate=Decimal("5.40"))
        client = TestClient(app)

        resp = _upload(client, "generic_usd_symbol.csv", params={"dry_run": "true"})
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["dry_run"] is True
        assert data["canonize_scheduled"] is False
        assert data["new_entry_ids"] == []

        from sqlalchemy.orm import Session

        with Session(engine) as session:
            assert session.query(UserCollectionRow).count() == 0

    def test_invalid_currency_rejected(self) -> None:
        engine = _create_test_db()
        app = _create_app(engine)
        client = TestClient(app)

        resp = _upload(client, "generic_usd_symbol.csv", params={"currency": "EUR"})
        assert resp.status_code == 422

    def test_liga_file_without_prices_defaults_to_brl_origin(self) -> None:
        engine = _create_test_db()
        app = _create_app(engine)
        client = TestClient(app)

        resp = _upload(client, "liga_brl_no_price.csv")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["priced"] == 0
        assert data["currency_source"] == "origin"
        assert data["imported"] == 3

    def test_liga_file_dry_run_reports_priced_zero(self) -> None:
        engine = _create_test_db()
        app = _create_app(engine)
        client = TestClient(app)

        resp = _upload(client, "liga_brl_no_price.csv", params={"dry_run": "true"})
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["priced"] == 0
        assert data["currency_source"] == "origin"
        assert data["dry_run"] is True

    def test_no_rate_available_returns_price_warnings(self) -> None:
        engine = _create_test_db()
        app = _create_app(engine, rate=None)
        client = TestClient(app)

        resp = _upload(client, "generic_usd_symbol.csv")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["converted"] == 0
        assert len(data["price_warnings"]) > 0

    def test_ambiguous_file_currency_override_usd(self) -> None:
        engine = _create_test_db()
        app = _create_app(engine, rate=Decimal("5.40"))
        client = TestClient(app)

        resp = _upload(client, "ambiguous_no_hint.csv", params={"currency": "USD"})
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["detected_currency"] == "USD"
        assert data["converted"] == 2

    def test_non_csv_file_still_rejected(self) -> None:
        engine = _create_test_db()
        app = _create_app(engine)
        client = TestClient(app)

        resp = client.post(
            "/api/v1/collection/import",
            files={"file": ("data.json", io.BytesIO(b"{}"), "application/json")},
        )
        assert resp.status_code == 400
