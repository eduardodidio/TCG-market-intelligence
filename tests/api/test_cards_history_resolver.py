"""F176-T09: ``GET /cards/{id}/history`` uses ``build_history`` (normal variant).

Covers cards whose only source is the Liga sweep (no ``source_cards`` row),
foil/normal isolation, source-priority merge (Liga beats MYP on the same
day), manual-price priority, and the empty/no-price edge cases.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.api.routers.cards import router
from src.database.models import CardRow, PriceObservationRow, SourceCardRow
from src.database.repository import Repository

TODAY = date(2026, 9, 24)


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test.db"
    return Repository(db_url=f"sqlite:///{db_path}")


@pytest.fixture()
def client(repo):
    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        yield repo

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _make_card(repo: Repository, name: str = "Card") -> int:
    with Session(repo.engine) as session:
        card = CardRow(game="magic", name_en=name, set_code="TST", collector_number="1")
        session.add(card)
        session.commit()
        return card.id


def _add_observation(
    repo: Repository,
    source: str,
    external_id: str,
    observed_at: date,
    median_price: Decimal | None,
) -> None:
    with Session(repo.engine) as session:
        session.add(
            PriceObservationRow(
                source=source,
                external_id=external_id,
                observed_at=observed_at,
                median_price=median_price,
                currency="BRL",
            )
        )
        session.commit()


class TestLigaOnlyCard:
    def test_card_only_liga_returns_points(self, repo, client):
        card_id = _make_card(repo, "Liga Only Card")
        _add_observation(repo, "liga", f"liga_{card_id}", TODAY - timedelta(days=5), Decimal("10.00"))

        resp = client.get(f"/cards/{card_id}/history")

        assert resp.status_code == 200
        observations = resp.json()["data"]["observations"]
        assert len(observations) == 1
        assert observations[0]["median_price"] == "10.00"


class TestVariantIsolation:
    def test_normal_series_never_includes_foil(self, repo, client):
        card_id = _make_card(repo, "Foil Mixed Card")
        _add_observation(repo, "liga", f"liga_{card_id}", TODAY - timedelta(days=3), Decimal("20.00"))
        _add_observation(
            repo, "liga", f"liga_{card_id}_foil", TODAY - timedelta(days=3), Decimal("99.00")
        )

        resp = client.get(f"/cards/{card_id}/history")

        body = resp.json()["data"]
        prices = [o["median_price"] for o in body["observations"]]
        assert "99.00" not in prices
        assert body["meta"]["variant"] == "normal"

    def test_foil_only_yields_empty_normal_series(self, repo, client):
        card_id = _make_card(repo, "Foil Only Card")
        _add_observation(
            repo, "liga", f"liga_{card_id}_foil", TODAY - timedelta(days=3), Decimal("99.00")
        )

        resp = client.get(f"/cards/{card_id}/history")

        body = resp.json()["data"]
        assert body["observations"] == []
        assert body["meta"]["first_observed_at"] is None


class TestSourcePriorityMerge:
    def test_liga_beats_myp_on_same_day(self, repo, client):
        card_id = _make_card(repo, "Multi Source Card")
        with Session(repo.engine) as session:
            session.add(
                SourceCardRow(
                    source="myp",
                    external_id="myp_ext",
                    card_id=card_id,
                    url="https://myp/ext",
                    name_en="Multi Source Card",
                    set_code="TST",
                    collector_number="1",
                )
            )
            session.commit()
        observed_day = TODAY - timedelta(days=2)
        _add_observation(repo, "liga", f"liga_{card_id}", observed_day, Decimal("15.00"))
        _add_observation(repo, "myp", "myp_ext", observed_day, Decimal("12.00"))

        resp = client.get(f"/cards/{card_id}/history")

        observations = resp.json()["data"]["observations"]
        assert len(observations) == 1
        assert observations[0]["median_price"] == "15.00"


class TestManualPriority:
    def test_manual_price_wins_over_liga(self, repo, client):
        card_id = _make_card(repo, "Manual Priced Card")
        observed_day = TODAY - timedelta(days=1)
        _add_observation(repo, "liga", f"liga_{card_id}", observed_day, Decimal("15.00"))
        _add_observation(repo, "manual", f"manual_{card_id}", observed_day, Decimal("42.00"))

        resp = client.get(f"/cards/{card_id}/history")

        observations = resp.json()["data"]["observations"]
        assert len(observations) == 1
        assert observations[0]["median_price"] == "42.00"


class TestEdgeCases:
    def test_nonexistent_card_returns_404(self, client):
        resp = client.get("/cards/999999/history")
        assert resp.status_code == 404

    def test_invalid_period_returns_422(self, repo, client):
        card_id = _make_card(repo)
        resp = client.get(f"/cards/{card_id}/history?period=3y")
        assert resp.status_code == 422

    def test_card_without_any_price_returns_empty_coherent_summary(self, repo, client):
        card_id = _make_card(repo, "No Price Card")

        resp = client.get(f"/cards/{card_id}/history")

        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["observations"] == []
        assert body["summary"]["data_points"] == 0
