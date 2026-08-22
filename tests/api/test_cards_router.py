from __future__ import annotations

import base64
from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.api.routers.cards import (
    decode_cursor,
    encode_cursor,
    router,
)
from src.database.models import (
    CardRow,
    PriceObservationRow,
    SourceCardRow,
)
from src.database.repository import Repository


@pytest.fixture()
def test_app(tmp_path):
    """Create a FastAPI test app with temp DB."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    repo = Repository(db_url=db_url)

    # Seed data
    engine = repo.engine
    with Session(engine) as session:
        c1 = CardRow(
            game="magic",
            name_en="Lightning Bolt",
            name_pt="Raio",
            set_code="2XM",
            collector_number="1",
        )
        c2 = CardRow(
            game="magic",
            name_en="Counterspell",
            name_pt="Contrafeitico",
            set_code="DMR",
            collector_number="44",
        )
        c3 = CardRow(
            game="pokemon",
            name_en="Pikachu",
            name_pt="Pikachu",
            set_code="SV1",
            collector_number="25",
        )
        session.add_all([c1, c2, c3])
        session.flush()

        sc1 = SourceCardRow(
            source="myp",
            external_id="ext1",
            card_id=c1.id,
            url="https://myp/ext1",
            name_en="Lightning Bolt",
            set_code="2XM",
            collector_number="1",
        )
        sc2 = SourceCardRow(
            source="myp",
            external_id="ext2",
            card_id=c2.id,
            url="https://myp/ext2",
            name_en="Counterspell",
            set_code="DMR",
            collector_number="44",
        )
        session.add_all([sc1, sc2])
        session.flush()

        obs1 = PriceObservationRow(
            source="myp",
            external_id="ext1",
            observed_at=date(2026, 8, 10),
            median_price=Decimal("5.50"),
            currency="BRL",
        )
        obs2 = PriceObservationRow(
            source="myp",
            external_id="ext1",
            observed_at=date(2026, 8, 15),
            median_price=Decimal("6.00"),
            currency="BRL",
        )
        obs3 = PriceObservationRow(
            source="myp",
            external_id="ext2",
            observed_at=date(2026, 8, 12),
            median_price=Decimal("3.00"),
            tcg_price=Decimal("2.80"),
            currency="BRL",
        )
        session.add_all([obs1, obs2, obs3])
        session.commit()

        test_ids = {
            "c1": c1.id,
            "c2": c2.id,
            "c3": c3.id,
        }

    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        yield repo

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    return client, test_ids


class TestCursorEncoding:
    def test_encode_decode_roundtrip(self):
        assert decode_cursor(encode_cursor(42)) == 42

    def test_decode_invalid_returns_none(self):
        assert decode_cursor("not-valid-base64!!!") is None

    def test_decode_non_integer_returns_none(self):
        encoded = base64.urlsafe_b64encode(b"abc").decode()
        assert decode_cursor(encoded) is None


class TestListCards:
    def test_list_all(self, test_app):
        client, _ = test_app
        resp = client.get("/cards")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 3
        assert body["meta"]["total"] == 3
        assert body["meta"]["cursor"] is None

    def test_filter_by_game(self, test_app):
        client, _ = test_app
        resp = client.get("/cards?game=magic")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 2
        assert body["meta"]["total"] == 2

    def test_filter_by_set(self, test_app):
        client, _ = test_app
        resp = client.get("/cards?set=DMR")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 1
        assert body["data"][0]["name_en"] == "Counterspell"

    def test_filter_by_name(self, test_app):
        client, _ = test_app
        resp = client.get("/cards?name=bolt")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 1
        assert body["data"][0]["name_en"] == "Lightning Bolt"

    def test_pagination_cursor(self, test_app):
        client, _ = test_app
        # Get first page with limit=1
        resp = client.get("/cards?limit=1")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 1
        assert body["meta"]["cursor"] is not None

        # Follow cursor
        cursor = body["meta"]["cursor"]
        resp2 = client.get(f"/cards?limit=1&cursor={cursor}")
        assert resp2.status_code == 200
        body2 = resp2.json()
        assert len(body2["data"]) == 1
        # Different card than first page
        assert body2["data"][0]["id"] != body["data"][0]["id"]

    def test_limit_too_high(self, test_app):
        client, _ = test_app
        resp = client.get("/cards?limit=201")
        assert resp.status_code == 422

    def test_limit_too_low(self, test_app):
        client, _ = test_app
        resp = client.get("/cards?limit=0")
        assert resp.status_code == 422

    def test_latest_price_included(self, test_app):
        client, _ = test_app
        resp = client.get("/cards?name=bolt")
        body = resp.json()
        card = body["data"][0]
        # Latest price for Lightning Bolt is 6.00
        assert card["latest_price"] is not None

    def test_no_price_card(self, test_app):
        client, _ = test_app
        resp = client.get("/cards?game=pokemon")
        body = resp.json()
        card = body["data"][0]
        assert card["latest_price"] is None


class TestGetCard:
    def test_found(self, test_app):
        client, ids = test_app
        resp = client.get(f"/cards/{ids['c1']}")
        assert resp.status_code == 200
        body = resp.json()
        data = body["data"]
        assert data["name_en"] == "Lightning Bolt"
        assert data["game"] == "magic"
        assert len(data["source_cards"]) == 1
        assert data["source_cards"][0]["source"] == "myp"
        assert data["created_at"] is not None

    def test_not_found(self, test_app):
        client, _ = test_app
        resp = client.get("/cards/99999")
        assert resp.status_code == 404

    def test_card_without_source_cards(self, test_app):
        client, ids = test_app
        resp = client.get(f"/cards/{ids['c3']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["source_cards"] == []
        assert body["data"]["latest_price"] is None


class TestGetHistory:
    def test_default_period(self, test_app):
        client, ids = test_app
        resp = client.get(f"/cards/{ids['c1']}/history")
        assert resp.status_code == 200
        body = resp.json()
        data = body["data"]
        observations = data["observations"]
        assert len(observations) == 2
        # Sorted by date ascending
        assert observations[0]["observed_at"] == "2026-08-10"
        assert observations[1]["observed_at"] == "2026-08-15"
        # Summary is present
        assert data["summary"] is not None
        assert data["summary"]["period"] == "90d"
        assert data["summary"]["data_points"] == 2

    def test_specific_period(self, test_app):
        client, ids = test_app
        resp = client.get(f"/cards/{ids['c2']}/history?period=30d")
        assert resp.status_code == 200
        body = resp.json()
        observations = body["data"]["observations"]
        assert len(observations) == 1
        assert observations[0]["median_price"] is not None

    def test_invalid_period(self, test_app):
        client, ids = test_app
        resp = client.get(f"/cards/{ids['c1']}/history?period=3y")
        assert resp.status_code == 422

    def test_24h_period_accepted(self, test_app):
        client, ids = test_app
        resp = client.get(f"/cards/{ids['c1']}/history?period=24h")
        assert resp.status_code == 200

    def test_7d_period_accepted(self, test_app):
        client, ids = test_app
        resp = client.get(f"/cards/{ids['c1']}/history?period=7d")
        assert resp.status_code == 200

    def test_nonexistent_card(self, test_app):
        client, _ = test_app
        resp = client.get("/cards/99999/history")
        assert resp.status_code == 404

    def test_card_without_source(self, test_app):
        client, ids = test_app
        resp = client.get(f"/cards/{ids['c3']}/history")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["observations"] == []

    def test_history_includes_fields(self, test_app):
        client, ids = test_app
        resp = client.get(f"/cards/{ids['c2']}/history")
        body = resp.json()
        obs = body["data"]["observations"][0]
        assert "observed_at" in obs
        assert "median_price" in obs
        assert "tcg_price" in obs
        assert "currency" in obs

    def test_history_response_includes_summary(self, test_app):
        client, ids = test_app
        resp = client.get(f"/cards/{ids['c1']}/history")
        body = resp.json()
        data = body["data"]
        assert "observations" in data
        assert "summary" in data
        summary = data["summary"]
        assert "period" in summary
        assert "price_start" in summary
        assert "price_end" in summary
        assert "absolute_change" in summary
        assert "percent_change" in summary
        assert "data_points" in summary
        assert "resolution" in summary
