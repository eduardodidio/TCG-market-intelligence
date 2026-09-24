"""Tests for GET /collection/{entry_id}/metrics endpoint — F34.

F176-T08: metrics now read from ``build_history`` (real DB), so the repo
here is a real sqlite ``Repository`` instead of a ``MagicMock`` — the
service layer queries ``Session(repo.engine)`` directly and cannot be
satisfied by mocking ``get_price_series``/``get_source_cards_for_card``.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.deps import get_currency_converter_dep, get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.database.models import CardRow, PriceObservationRow, UserCollectionRow
from src.database.repository import Repository
from src.services.currency import CurrencyConverter

_TEST_USER_ID = "eduardo"


def _make_repo(tmp_path) -> Repository:
    db_path = tmp_path / "test.db"
    return Repository(db_url=f"sqlite:///{db_path}")


def _make_card(repo: Repository, name_en: str = "Lightning Bolt") -> int:
    with Session(repo.engine) as session:
        card = CardRow(game="magic", name_en=name_en, set_code="DMR", collector_number="123")
        session.add(card)
        session.commit()
        return card.id


def _make_collection_entry(repo: Repository, card_id: int | None, **overrides) -> int:
    defaults = {
        "user_id": _TEST_USER_ID,
        "card_id": card_id,
        "set_code": "DMR",
        "collector_number": "123",
        "name_en": "Lightning Bolt",
        "name_pt": "Raio",
        "set_name_en": "Dominaria Remastered",
        "quantity": 2,
        "quality": "NM",
        "language": "EN",
        "rarity": "R",
        "color": "R",
        "extras": None,
    }
    defaults.update(overrides)
    with Session(repo.engine) as session:
        entry = UserCollectionRow(**defaults)
        session.add(entry)
        session.commit()
        return entry.id


def _add_price_series(repo: Repository, card_id: int, n_days: int) -> None:
    today = date.today()
    with Session(repo.engine) as session:
        for i in range(n_days):
            session.add(
                PriceObservationRow(
                    source="liga",
                    external_id=f"liga_{card_id}",
                    observed_at=today - timedelta(days=n_days - i),
                    median_price=Decimal("10") + Decimal(str(i)),
                    currency="BRL",
                )
            )
        session.commit()


def _make_converter(repo: Repository) -> CurrencyConverter:
    """Real converter — BRL/PILA pass through unchanged, same as the mock did."""
    return CurrencyConverter(repo)


def _make_app(repo: Repository, user_id: str = _TEST_USER_ID) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: user_id
    app.dependency_overrides[get_currency_converter_dep] = lambda: _make_converter(repo)
    return app


def _setup_with_prices(tmp_path, n_days: int = 30) -> tuple[Repository, int]:
    """Setup a real repo with an entry linked to a card with n_days of price data."""
    repo = _make_repo(tmp_path)
    card_id = _make_card(repo)
    entry_id = _make_collection_entry(repo, card_id)
    _add_price_series(repo, card_id, n_days)
    return repo, entry_id


class TestGetCardMetrics:
    def test_returns_200_with_valid_data(self, tmp_path) -> None:
        repo, entry_id = _setup_with_prices(tmp_path, 30)
        app = _make_app(repo)
        client = TestClient(app)

        resp = client.get(f"/collection/{entry_id}/metrics?period=30d")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["entry_id"] == entry_id
        assert data["period"] == "30d"
        assert data["currency"] == "BRL"
        assert data["data_points"] == 30

    def test_contains_all_metric_fields(self, tmp_path) -> None:
        repo, entry_id = _setup_with_prices(tmp_path, 60)
        app = _make_app(repo)
        client = TestClient(app)

        resp = client.get(f"/collection/{entry_id}/metrics?period=30d")
        data = resp.json()["data"]

        assert "moving_averages" in data
        assert "extremes" in data
        assert "volatility" in data
        assert "momentum" in data
        assert "performance" in data
        assert "period_comparison" in data

    def test_extremes_populated(self, tmp_path) -> None:
        repo, entry_id = _setup_with_prices(tmp_path, 30)
        app = _make_app(repo)
        client = TestClient(app)

        resp = client.get(f"/collection/{entry_id}/metrics?period=30d")
        data = resp.json()["data"]

        assert data["extremes"] is not None
        assert "ath_price" in data["extremes"]
        assert "atl_price" in data["extremes"]
        assert "ath_date" in data["extremes"]
        assert "atl_date" in data["extremes"]

    def test_momentum_populated(self, tmp_path) -> None:
        repo, entry_id = _setup_with_prices(tmp_path, 30)
        app = _make_app(repo)
        client = TestClient(app)

        resp = client.get(f"/collection/{entry_id}/metrics?period=30d")
        data = resp.json()["data"]

        assert data["momentum"] is not None
        assert "rate_of_change" in data["momentum"]
        assert "trend_direction" in data["momentum"]

    def test_null_fields_when_insufficient_data(self, tmp_path) -> None:
        repo = _make_repo(tmp_path)
        card_id = _make_card(repo)
        entry_id = _make_collection_entry(repo, card_id)
        with Session(repo.engine) as session:
            session.add(
                PriceObservationRow(
                    source="liga",
                    external_id=f"liga_{card_id}",
                    observed_at=date.today(),
                    median_price=Decimal("10"),
                    currency="BRL",
                )
            )
            session.commit()

        app = _make_app(repo)
        client = TestClient(app)

        resp = client.get(f"/collection/{entry_id}/metrics?period=30d")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["volatility"] is None
        assert data["momentum"] is None
        assert data["performance"] is None

    def test_404_for_nonexistent_entry(self, tmp_path) -> None:
        repo = _make_repo(tmp_path)
        app = _make_app(repo)
        client = TestClient(app)

        resp = client.get("/collection/999/metrics")
        assert resp.status_code == 404

    def test_404_for_other_users_entry(self, tmp_path) -> None:
        repo = _make_repo(tmp_path)
        card_id = _make_card(repo)
        entry_id = _make_collection_entry(repo, card_id, user_id="other_user")
        app = _make_app(repo)
        client = TestClient(app)

        resp = client.get(f"/collection/{entry_id}/metrics")
        assert resp.status_code == 404

    def test_422_when_card_not_linked(self, tmp_path) -> None:
        repo = _make_repo(tmp_path)
        entry_id = _make_collection_entry(repo, None)
        app = _make_app(repo)
        client = TestClient(app)

        resp = client.get(f"/collection/{entry_id}/metrics")
        assert resp.status_code == 422

    def test_invalid_period_returns_422(self, tmp_path) -> None:
        repo, entry_id = _setup_with_prices(tmp_path, 30)
        app = _make_app(repo)
        client = TestClient(app)

        resp = client.get(f"/collection/{entry_id}/metrics?period=invalid")
        assert resp.status_code == 422

    def test_different_periods(self, tmp_path) -> None:
        repo, entry_id = _setup_with_prices(tmp_path, 60)
        app = _make_app(repo)
        client = TestClient(app)

        resp_7d = client.get(f"/collection/{entry_id}/metrics?period=7d")
        resp_90d = client.get(f"/collection/{entry_id}/metrics?period=90d")

        assert resp_7d.status_code == 200
        assert resp_90d.status_code == 200

        data_7d = resp_7d.json()["data"]
        data_90d = resp_90d.json()["data"]
        assert data_7d["period"] == "7d"
        assert data_90d["period"] == "90d"

    def test_all_valid_periods(self, tmp_path) -> None:
        repo, entry_id = _setup_with_prices(tmp_path, 30)
        app = _make_app(repo)
        client = TestClient(app)

        for period in ("24h", "7d", "30d", "90d", "180d", "1y"):
            resp = client.get(f"/collection/{entry_id}/metrics?period={period}")
            assert resp.status_code == 200, f"Period {period} failed"

    def test_empty_source_cards_returns_empty_metrics(self, tmp_path) -> None:
        repo = _make_repo(tmp_path)
        card_id = _make_card(repo)
        entry_id = _make_collection_entry(repo, card_id)
        app = _make_app(repo)
        client = TestClient(app)

        resp = client.get(f"/collection/{entry_id}/metrics?period=30d")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["data_points"] == 0

    def test_follows_api_response_envelope(self, tmp_path) -> None:
        repo, entry_id = _setup_with_prices(tmp_path, 30)
        app = _make_app(repo)
        client = TestClient(app)

        resp = client.get(f"/collection/{entry_id}/metrics?period=30d")
        body = resp.json()
        assert "data" in body
        assert "meta" in body
