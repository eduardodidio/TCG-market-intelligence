"""F176-T08: ``/collection/{id}/history`` and ``/collection/{id}/metrics`` use ``build_history``.

Covers collection entries whose card only has Liga-sweep prices (no
``source_cards`` row — previously returned 0 points, ADR 0017 H1), foil/normal
isolation, ``daily_snapshot`` carry-forward points, ownership checks and the
unchanged 422/empty-card behaviors.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.deps import get_currency_converter_dep, get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.database.models import CardRow, PriceObservationRow, UserCollectionRow
from src.services.currency import CurrencyConverter

TODAY = date(2026, 9, 24)
_USER = "eduardo"


@pytest.fixture()
def repo(tmp_path):
    from src.database.repository import Repository

    db_path = tmp_path / "test.db"
    return Repository(db_url=f"sqlite:///{db_path}")


@pytest.fixture()
def client(repo):
    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: _USER
    app.dependency_overrides[get_currency_converter_dep] = lambda: CurrencyConverter(repo)
    return TestClient(app)


def _make_card(repo, name: str = "Card") -> int:
    with Session(repo.engine) as session:
        card = CardRow(game="magic", name_en=name, set_code="TST", collector_number="1")
        session.add(card)
        session.commit()
        return card.id


def _make_collection_entry(repo, card_id: int | None, *, user_id: str = _USER, extras=None) -> int:
    with Session(repo.engine) as session:
        entry = UserCollectionRow(
            user_id=user_id,
            card_id=card_id,
            set_code="TST",
            collector_number="1",
            extras=extras,
        )
        session.add(entry)
        session.commit()
        return entry.id


def _add_observation(
    repo, source: str, external_id: str, observed_at: date, median_price, currency="BRL"
) -> None:
    with Session(repo.engine) as session:
        session.add(
            PriceObservationRow(
                source=source,
                external_id=external_id,
                observed_at=observed_at,
                median_price=Decimal(str(median_price)) if median_price is not None else None,
                currency=currency,
            )
        )
        session.commit()


class TestLigaOnlyEntry:
    def test_liga_only_card_returns_points(self, repo, client):
        card_id = _make_card(repo, "Liga Only Card")
        for i in range(3):
            _add_observation(repo, "liga", f"liga_{card_id}", TODAY - timedelta(days=i), "10.00")
        entry_id = _make_collection_entry(repo, card_id)

        resp = client.get(f"/collection/{entry_id}/history?period=30d")

        assert resp.status_code == 200
        body = resp.json()["data"]
        assert len(body["observations"]) == 3
        assert body["meta"]["sources"] == ["liga"]

    def test_metrics_has_data_points_for_liga_only_card(self, repo, client):
        card_id = _make_card(repo, "Liga Only Card")
        for i in range(3):
            _add_observation(repo, "liga", f"liga_{card_id}", TODAY - timedelta(days=i), "10.00")
        entry_id = _make_collection_entry(repo, card_id)

        resp = client.get(f"/collection/{entry_id}/metrics?period=30d")

        assert resp.status_code == 200
        assert resp.json()["data"]["data_points"] > 0


class TestFoilIsolation:
    def test_foil_entry_only_sees_foil_series(self, repo, client):
        card_id = _make_card(repo, "Foil Card")
        _add_observation(repo, "liga", f"liga_{card_id}_foil", TODAY - timedelta(days=1), "100.00")
        _add_observation(repo, "liga", f"liga_{card_id}", TODAY - timedelta(days=1), "10.00")
        entry_id = _make_collection_entry(repo, card_id, extras="Foil")

        resp = client.get(f"/collection/{entry_id}/history?period=30d")

        body = resp.json()["data"]
        prices = [o["median_price"] for o in body["observations"]]
        assert prices == ["100.00"]
        assert body["meta"]["variant"] == "foil"


class TestDailySnapshot:
    def test_daily_snapshot_source_is_exposed(self, repo, client):
        card_id = _make_card(repo, "Snapshot Card")
        _add_observation(repo, "liga", f"liga_{card_id}", TODAY - timedelta(days=5), "10.00")
        _add_observation(
            repo, "daily_snapshot", f"liga_{card_id}", TODAY - timedelta(days=3), "10.00"
        )
        entry_id = _make_collection_entry(repo, card_id)

        resp = client.get(f"/collection/{entry_id}/history?period=30d")

        observations = resp.json()["data"]["observations"]
        sources = {o["source"] for o in observations}
        assert "daily_snapshot" in sources


class TestEdgeCases:
    def test_card_id_none_returns_empty_history_no_meta(self, repo, client):
        entry_id = _make_collection_entry(repo, None)

        resp = client.get(f"/collection/{entry_id}/history?period=30d")

        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["observations"] == []
        assert body["meta"] is None

    def test_card_id_none_metrics_returns_422(self, repo, client):
        entry_id = _make_collection_entry(repo, None)

        resp = client.get(f"/collection/{entry_id}/metrics?period=30d")

        assert resp.status_code == 422

    def test_other_users_entry_returns_404(self, repo, client):
        card_id = _make_card(repo)
        entry_id = _make_collection_entry(repo, card_id, user_id="someone-else")

        resp = client.get(f"/collection/{entry_id}/history?period=30d")

        assert resp.status_code == 404

    def test_invalid_period_returns_422(self, repo, client):
        card_id = _make_card(repo)
        entry_id = _make_collection_entry(repo, card_id)

        resp = client.get(f"/collection/{entry_id}/history?period=abc")

        assert resp.status_code == 422

    def test_card_without_prices_has_empty_observations_and_meta(self, repo, client):
        card_id = _make_card(repo, "No Price Card")
        entry_id = _make_collection_entry(repo, card_id)

        resp = client.get(f"/collection/{entry_id}/history?period=30d")

        body = resp.json()["data"]
        assert body["observations"] == []
        assert body["meta"]["first_observed_at"] is None
        assert body["meta"]["variant"] == "normal"

    def test_metrics_no_prices_has_zero_data_points(self, repo, client):
        card_id = _make_card(repo, "No Price Card")
        entry_id = _make_collection_entry(repo, card_id)

        resp = client.get(f"/collection/{entry_id}/metrics?period=30d")

        assert resp.status_code == 200
        assert resp.json()["data"]["data_points"] == 0
