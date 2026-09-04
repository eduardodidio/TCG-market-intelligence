"""Tests for the catalog REST API endpoints (F103-T06)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.deps import get_db
from src.api.routers.catalog import router
from src.database.models import Base, CardRow, PriceObservationRow, SourceCardRow
from src.database.repository import Repository

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_repo():
    """Create an in-memory SQLite DB with test data."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # --- Cards (5 cards, 2 sets) ---
        cards = [
            CardRow(
                id=1,
                game="magic",
                name_en="Lightning Bolt",
                name_pt="Raio",
                set_code="lea",
                collector_number="161",
                rarity="C",
                color_identity="R",
                mana_cost="{R}",
                type_line="Instant",
                image_uri="https://example.com/bolt.jpg",
            ),
            CardRow(
                id=2,
                game="magic",
                name_en="Counterspell",
                name_pt="Contrafeitico",
                set_code="lea",
                collector_number="54",
                rarity="U",
                color_identity="U",
                mana_cost="{U}{U}",
                type_line="Instant",
                image_uri="https://example.com/counter.jpg",
            ),
            CardRow(
                id=3,
                game="magic",
                name_en="Dark Ritual",
                name_pt="Ritual Sombrio",
                set_code="lea",
                collector_number="98",
                rarity="C",
                color_identity="B",
                mana_cost="{B}",
                type_line="Instant",
                image_uri="https://example.com/ritual.jpg",
            ),
            CardRow(
                id=4,
                game="magic",
                name_en="Sol Ring",
                name_pt="Anel Solar",
                set_code="cmd",
                collector_number="261",
                rarity="U",
                color_identity="",
                mana_cost="{1}",
                type_line="Artifact",
                image_uri="https://example.com/sol.jpg",
            ),
            CardRow(
                id=5,
                game="magic",
                name_en="Forest",
                name_pt="Floresta",
                set_code="cmd",
                collector_number="310",
                rarity="C",
                color_identity="G",
                mana_cost="",
                type_line="Basic Land - Forest",
                image_uri="https://example.com/forest.jpg",
            ),
        ]
        session.add_all(cards)
        session.flush()

        # --- Source cards (Liga entries for cards 1, 2, 4) ---
        source_cards = [
            SourceCardRow(
                id=1,
                source="liga",
                external_id="liga_1",
                card_id=1,
                url="https://liga.com/bolt",
                name_en="Lightning Bolt",
            ),
            SourceCardRow(
                id=2,
                source="liga",
                external_id="liga_2",
                card_id=2,
                url="https://liga.com/counter",
                name_en="Counterspell",
            ),
            SourceCardRow(
                id=3,
                source="liga",
                external_id="liga_4",
                card_id=4,
                url="https://liga.com/sol",
                name_en="Sol Ring",
            ),
        ]
        session.add_all(source_cards)
        session.flush()

        # --- Price observations (cards 1 and 4 have prices) ---
        observations = [
            PriceObservationRow(
                source="liga",
                external_id="liga_1",
                observed_at=date(2026, 9, 1),
                median_price=Decimal("5.00"),
                currency="BRL",
            ),
            PriceObservationRow(
                source="liga",
                external_id="liga_1",
                observed_at=date(2026, 9, 3),
                median_price=Decimal("6.50"),
                currency="BRL",
            ),
            PriceObservationRow(
                source="liga",
                external_id="liga_4",
                observed_at=date(2026, 9, 2),
                median_price=Decimal("25.00"),
                currency="BRL",
            ),
        ]
        session.add_all(observations)
        session.commit()

    # Create a Repository that uses our engine
    repo = Repository.__new__(Repository)
    repo.engine = engine
    return repo


@pytest.fixture()
def client(db_repo: Repository) -> TestClient:
    """Create a TestClient with the catalog router and in-memory DB."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_repo
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /catalog/cards — list
# ---------------------------------------------------------------------------


class TestListCatalogCards:
    def test_returns_all_magic_cards(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/cards")
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["total"] == 5
        assert len(body["items"]) == 5

    def test_default_pagination(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/cards")
        body = resp.json()["data"]
        assert body["limit"] == 50
        assert body["offset"] == 0

    def test_limit_and_offset(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/cards?limit=2&offset=2")
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["limit"] == 2
        assert body["offset"] == 2
        assert len(body["items"]) == 2
        assert body["total"] == 5

    def test_filter_by_set_code(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/cards?set_code=lea")
        body = resp.json()["data"]
        assert body["total"] == 3
        for item in body["items"]:
            assert item["set_code"] == "lea"

    def test_filter_by_rarity(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/cards?rarity=U")
        body = resp.json()["data"]
        assert body["total"] == 2
        names = {item["name_en"] for item in body["items"]}
        assert names == {"Counterspell", "Sol Ring"}

    def test_filter_by_color_contains(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/cards?color=R")
        body = resp.json()["data"]
        assert body["total"] == 1
        assert body["items"][0]["name_en"] == "Lightning Bolt"

    def test_filter_by_name_like(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/cards?name=bolt")
        body = resp.json()["data"]
        assert body["total"] == 1
        assert body["items"][0]["name_en"] == "Lightning Bolt"

    def test_filter_by_name_pt(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/cards?name=Raio")
        body = resp.json()["data"]
        assert body["total"] == 1
        assert body["items"][0]["name_pt"] == "Raio"

    def test_filter_has_price_true(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/cards?has_price=true")
        body = resp.json()["data"]
        assert body["total"] == 2
        names = {item["name_en"] for item in body["items"]}
        assert names == {"Lightning Bolt", "Sol Ring"}

    def test_filter_has_price_false(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/cards?has_price=false")
        body = resp.json()["data"]
        assert body["total"] == 3
        for item in body["items"]:
            assert item["liga_price"] is None

    def test_filter_min_price(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/cards?min_price=10")
        body = resp.json()["data"]
        assert body["total"] == 1
        assert body["items"][0]["name_en"] == "Sol Ring"

    def test_filter_max_price(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/cards?max_price=10")
        body = resp.json()["data"]
        assert body["total"] == 1
        assert body["items"][0]["name_en"] == "Lightning Bolt"

    def test_sort_by_name_asc(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/cards?sort_by=name&sort_dir=asc")
        body = resp.json()["data"]
        names = [item["name_en"] for item in body["items"]]
        assert names == sorted(names)

    def test_sort_by_name_desc(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/cards?sort_by=name&sort_dir=desc")
        body = resp.json()["data"]
        names = [item["name_en"] for item in body["items"]]
        assert names == sorted(names, reverse=True)

    def test_sort_by_price(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/cards?sort_by=price&sort_dir=asc")
        body = resp.json()["data"]
        # Priced cards come first, nulls at end
        priced = [item for item in body["items"] if item["liga_price"] is not None]
        unpriced = [item for item in body["items"] if item["liga_price"] is None]
        assert len(priced) == 2
        assert len(unpriced) == 3
        # Priced should be ascending
        assert priced[0]["liga_price"] <= priced[1]["liga_price"]

    def test_card_without_price_returns_null(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/cards?name=Dark Ritual")
        body = resp.json()["data"]
        assert body["total"] == 1
        item = body["items"][0]
        assert item["liga_price"] is None
        assert item["liga_price_date"] is None

    def test_card_with_price_returns_latest(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/cards?name=Lightning Bolt")
        body = resp.json()["data"]
        item = body["items"][0]
        # Should be latest price (6.50 from 2026-09-03), not older (5.00)
        assert item["liga_price"] == 6.5
        assert "2026-09-03" in item["liga_price_date"]

    def test_limit_max_200(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/cards?limit=300")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /catalog/cards/{card_id} — detail
# ---------------------------------------------------------------------------


class TestGetCatalogCard:
    def test_returns_card_with_price(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/cards/1")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name_en"] == "Lightning Bolt"
        assert data["liga_price"] == 6.5
        assert data["image_uri"] == "https://example.com/bolt.jpg"

    def test_returns_card_without_price(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/cards/3")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name_en"] == "Dark Ritual"
        assert data["liga_price"] is None
        assert data["liga_price_date"] is None

    def test_returns_404_for_missing_card(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/cards/999")
        assert resp.status_code == 404

    def test_returns_all_card_fields(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/cards/4")
        data = resp.json()["data"]
        assert data["id"] == 4
        assert data["name_en"] == "Sol Ring"
        assert data["name_pt"] == "Anel Solar"
        assert data["set_code"] == "cmd"
        assert data["collector_number"] == "261"
        assert data["rarity"] == "U"
        assert data["color_identity"] == ""
        assert data["mana_cost"] == "{1}"
        assert data["type_line"] == "Artifact"
        assert data["liga_price"] == 25.0


# ---------------------------------------------------------------------------
# GET /catalog/sets
# ---------------------------------------------------------------------------


class TestListCatalogSets:
    def test_returns_sets_ordered(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/sets")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 2
        codes = [s["set_code"] for s in data]
        assert codes == sorted(codes)

    def test_correct_card_counts(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/sets")
        data = resp.json()["data"]
        sets_by_code = {s["set_code"]: s for s in data}

        assert sets_by_code["lea"]["card_count"] == 3
        assert sets_by_code["cmd"]["card_count"] == 2

    def test_correct_priced_counts(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/sets")
        data = resp.json()["data"]
        sets_by_code = {s["set_code"]: s for s in data}

        # lea: cards 1 (priced), 2 (source but no price), 3 (no source)
        assert sets_by_code["lea"]["priced_count"] == 1
        # cmd: card 4 (priced), card 5 (no source)
        assert sets_by_code["cmd"]["priced_count"] == 1


# ---------------------------------------------------------------------------
# GET /catalog/stats
# ---------------------------------------------------------------------------


class TestGetCatalogStats:
    def test_returns_correct_totals(self, client: TestClient) -> None:
        resp = client.get("/api/v1/catalog/stats")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_cards"] == 5
        assert data["total_sets"] == 2
        assert data["cards_with_price"] == 2
        assert data["cards_without_price"] == 3

    def test_stats_empty_database(self) -> None:
        """Stats endpoint returns zeros when the catalog is empty."""
        engine = create_engine(
            "sqlite:///:memory:",
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        repo = Repository.__new__(Repository)
        repo.engine = engine

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_db] = lambda: repo
        empty_client = TestClient(app)

        resp = empty_client.get("/api/v1/catalog/stats")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_cards"] == 0
        assert data["total_sets"] == 0
        assert data["cards_with_price"] == 0
        assert data["cards_without_price"] == 0


# ---------------------------------------------------------------------------
# Multi-color filter edge cases
# ---------------------------------------------------------------------------


class TestMultiColorFilter:
    """Test comma-separated color filter in /catalog/cards."""

    @pytest.fixture(autouse=True)
    def _setup(self, client: TestClient) -> None:
        self.client = client

    def test_multi_color_comma_separated(self) -> None:
        """Filtering by 'R,U' should return no cards (no card has both R and U)."""
        resp = self.client.get("/api/v1/catalog/cards?color=R,U")
        body = resp.json()["data"]
        # In the test data: R=Lightning Bolt, U=Counterspell, B=Dark Ritual,
        # ""=Sol Ring, G=Forest. No card has both R and U.
        assert body["total"] == 0

    def test_single_color_filter_returns_match(self) -> None:
        """Single color 'B' returns Dark Ritual."""
        resp = self.client.get("/api/v1/catalog/cards?color=B")
        body = resp.json()["data"]
        assert body["total"] == 1
        assert body["items"][0]["name_en"] == "Dark Ritual"

    def test_color_filter_empty_identity(self) -> None:
        """Color filter should NOT match cards with empty color_identity."""
        resp = self.client.get("/api/v1/catalog/cards?color=W")
        body = resp.json()["data"]
        # Only Sol Ring has "", Forest has G — no card has W
        assert body["total"] == 0

    def test_color_filter_g_returns_forest(self) -> None:
        """Single color 'G' returns Forest."""
        resp = self.client.get("/api/v1/catalog/cards?color=G")
        body = resp.json()["data"]
        assert body["total"] == 1
        assert body["items"][0]["name_en"] == "Forest"


# ---------------------------------------------------------------------------
# Rarity filter edge cases
# ---------------------------------------------------------------------------


class TestRarityFilterCodes:
    """Test rarity filter with actual DB codes."""

    @pytest.fixture(autouse=True)
    def _setup(self, client: TestClient) -> None:
        self.client = client

    def test_rarity_common(self) -> None:
        """Rarity 'C' returns the 3 common cards."""
        resp = self.client.get("/api/v1/catalog/cards?rarity=C")
        body = resp.json()["data"]
        assert body["total"] == 3
        names = {item["name_en"] for item in body["items"]}
        assert names == {"Lightning Bolt", "Dark Ritual", "Forest"}

    def test_rarity_mythic_returns_empty(self) -> None:
        """Rarity 'M' returns 0 cards (none in test data)."""
        resp = self.client.get("/api/v1/catalog/cards?rarity=M")
        body = resp.json()["data"]
        assert body["total"] == 0

    def test_rarity_rare_returns_empty(self) -> None:
        """Rarity 'R' returns 0 cards (none in test data)."""
        resp = self.client.get("/api/v1/catalog/cards?rarity=R")
        body = resp.json()["data"]
        assert body["total"] == 0
