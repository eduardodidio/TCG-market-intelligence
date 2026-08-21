from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_db
from src.api.routers.collection import router
from src.database.models import PriceObservationRow, SourceCardRow, UserCollectionRow


def _make_collection_row(**overrides) -> MagicMock:
    """Build a mock UserCollectionRow with sensible defaults."""
    defaults = {
        "id": 1,
        "user_id": "eduardo",
        "card_id": 42,
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
        "extras": "Foil",
        "created_at": datetime(2026, 1, 1),
    }
    defaults.update(overrides)
    row = MagicMock(spec=UserCollectionRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_source_card(**overrides) -> MagicMock:
    defaults = {
        "id": 10,
        "source": "myp",
        "external_id": "99999",
        "card_id": 42,
        "sku": "magic_dmr_123",
        "url": "https://mypcards.com/magic/99999/lightning-bolt",
        "name_en": "Lightning Bolt",
        "name_pt": "Raio",
        "set_code": "DMR",
        "collector_number": "123",
    }
    defaults.update(overrides)
    sc = MagicMock(spec=SourceCardRow)
    for k, v in defaults.items():
        setattr(sc, k, v)
    return sc


def _make_price_obs(**overrides) -> MagicMock:
    defaults = {
        "id": 100,
        "source": "myp",
        "external_id": "99999",
        "observed_at": date(2026, 8, 20),
        "median_price": Decimal("8.50"),
        "tcg_price": Decimal("7.00"),
        "last_sold_price": Decimal("9.00"),
        "quantity_available": 5,
        "last_sold_meta": None,
        "currency": "BRL",
    }
    defaults.update(overrides)
    obs = MagicMock(spec=PriceObservationRow)
    for k, v in defaults.items():
        setattr(obs, k, v)
    return obs


def _make_app(mock_repo: MagicMock) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    return app


class TestGetCollectionEntry:
    """GET /collection/{entry_id} — detail endpoint."""

    def test_returns_full_entry_data(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row()
        source_card = _make_source_card()
        mock_repo.get_source_cards_for_card.return_value = [source_card]
        price_obs = _make_price_obs()
        mock_repo.get_latest_prices_batch.return_value = {42: price_obs}
        mock_repo.get_price_series.return_value = []

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/1")
        assert resp.status_code == 200

        body = resp.json()
        data = body["data"]
        assert data["id"] == 1
        assert data["name_en"] == "Lightning Bolt"
        assert data["name_pt"] == "Raio"
        assert data["set_code"] == "DMR"
        assert data["collector_number"] == "123"
        assert data["quantity"] == 2
        assert data["quality"] == "NM"
        assert data["language"] == "EN"
        assert data["extras"] == "Foil"
        assert data["card_id"] == 42

    def test_returns_404_for_nonexistent(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = None

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/999")
        assert resp.status_code == 404

    def test_linked_entry_includes_image_url_with_mapped_set(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row()
        mock_repo.get_source_cards_for_card.return_value = []
        mock_repo.get_latest_prices_batch.return_value = {}
        mock_repo.get_price_series.return_value = []

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/1")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert "image_url" in data
        assert "api.scryfall.com/cards/" in data["image_url"]
        assert "123" in data["image_url"]

    def test_linked_entry_includes_source_cards(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row()
        source_card = _make_source_card()
        mock_repo.get_source_cards_for_card.return_value = [source_card]
        mock_repo.get_latest_prices_batch.return_value = {42: _make_price_obs()}
        mock_repo.get_price_series.return_value = []

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/1")
        data = resp.json()["data"]

        assert len(data["source_cards"]) == 1
        assert data["source_cards"][0]["source"] == "myp"
        assert data["source_cards"][0]["external_id"] == "99999"

    def test_unlinked_entry_returns_null_price_fields(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row(card_id=None)

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/1")
        data = resp.json()["data"]

        assert data["card_id"] is None
        assert data["latest_price"] is None
        assert data["source_cards"] == []
        assert data["price_history"] == []

    def test_returns_external_links(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row()
        mock_repo.get_source_cards_for_card.return_value = []
        mock_repo.get_latest_prices_batch.return_value = {}

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/1")
        data = resp.json()["data"]

        assert data["scryfall_url"] is not None
        assert "scryfall.com" in data["scryfall_url"]
        assert "Lightning Bolt" in data["scryfall_url"]

        assert data["ligamagic_url"] is not None
        assert "ligamagic.com.br" in data["ligamagic_url"]
        assert "Lightning Bolt" in data["ligamagic_url"]

    def test_external_links_with_special_chars_in_name(self) -> None:
        """Card names with spaces and special chars appear in URLs.

        This documents that scryfall_url is NOT url-encoded (known MINOR issue).
        """
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row(
            name_en="Jace, the Mind Sculptor",
            name_pt=None,
        )
        mock_repo.get_source_cards_for_card.return_value = []
        mock_repo.get_latest_prices_batch.return_value = {}

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/1")
        data = resp.json()["data"]

        # Scryfall URL includes the name with space and comma (not encoded)
        assert data["scryfall_url"] is not None
        assert "Jace, the Mind Sculptor" in data["scryfall_url"]
        # LigaMagic URL also includes unencoded name
        assert data["ligamagic_url"] is not None
        assert "Jace, the Mind Sculptor" in data["ligamagic_url"]

    def test_no_external_links_when_name_is_empty(self) -> None:
        """Entry with no name_en and no name_pt produces null external links."""
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row(
            name_en=None,
            name_pt=None,
        )
        mock_repo.get_source_cards_for_card.return_value = []
        mock_repo.get_latest_prices_batch.return_value = {}

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/1")
        data = resp.json()["data"]

        assert data["scryfall_url"] is None
        assert data["ligamagic_url"] is None

    def test_variant_set_code_mapped_in_image_url(self) -> None:
        """Detail endpoint maps variant set codes in the image_url field."""
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row(
            set_code="bldmr",
            collector_number="437",
            card_id=None,
        )

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/1")
        data = resp.json()["data"]

        # bldmr should be mapped to dmr
        assert "/cards/dmr/437?" in data["image_url"]
