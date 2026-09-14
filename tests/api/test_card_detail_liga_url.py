"""Tests for Liga Magic URL in the CardDetail API endpoint (/api/v1/cards/{id}).

Verifies that the backend returns a properly built ligamagic_url,
especially for split/DFC cards and special characters.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_currency_converter_dep, get_db, get_optional_user
from src.api.routers.cards import router
from src.database.models import CardRow


def _make_card_row(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "game": "magic",
        "name_en": "Lightning Bolt",
        "name_pt": "Raio",
        "set_code": "DMR",
        "collector_number": "123",
        "created_at": datetime(2026, 1, 1),
        "updated_at": datetime(2026, 1, 1),
    }
    defaults.update(overrides)
    row = MagicMock(spec=CardRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_converter() -> MagicMock:
    converter = MagicMock()
    converter.convert.return_value = None
    return converter


def _make_app(mock_repo: MagicMock) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[get_optional_user] = lambda: None
    app.dependency_overrides[get_currency_converter_dep] = _make_converter
    return app


class TestCardDetailLigaUrl:
    """Liga URL must be present and correctly built in CardDetail response."""

    def test_normal_card_has_ligamagic_url(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_card_by_id.return_value = _make_card_row(
            name_en="Lightning Bolt",
        )
        mock_repo.get_source_cards_for_card.return_value = []
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/cards/1")
        data = resp.json()["data"]

        assert data["ligamagic_url"] is not None
        assert "Lightning+Bolt" in data["ligamagic_url"]
        assert "&show=1" in data["ligamagic_url"]

    def test_split_card_uses_front_face_only(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_card_by_id.return_value = _make_card_row(
            name_en="Painter's Studio // Defaced Gallery",
        )
        mock_repo.get_source_cards_for_card.return_value = []
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/cards/1")
        data = resp.json()["data"]

        assert "Painter%27s+Studio" in data["ligamagic_url"]
        assert "Defaced" not in data["ligamagic_url"]
        assert "&show=1" in data["ligamagic_url"]

    def test_card_with_comma(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_card_by_id.return_value = _make_card_row(
            name_en="Thalia, Guardian of Thraben",
        )
        mock_repo.get_source_cards_for_card.return_value = []
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/cards/1")
        data = resp.json()["data"]

        assert "Thalia%2C+Guardian+of+Thraben" in data["ligamagic_url"]
        assert "&show=1" in data["ligamagic_url"]

    def test_dfc_with_comma(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_card_by_id.return_value = _make_card_row(
            name_en="Beorn, Reluctant Host // Till and Tend",
        )
        mock_repo.get_source_cards_for_card.return_value = []
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/cards/1")
        data = resp.json()["data"]

        assert "Beorn%2C+Reluctant+Host" in data["ligamagic_url"]
        assert "Till" not in data["ligamagic_url"]

    def test_card_with_apostrophe(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_card_by_id.return_value = _make_card_row(
            name_en="Frodo's Ring",
        )
        mock_repo.get_source_cards_for_card.return_value = []
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/cards/1")
        data = resp.json()["data"]

        assert "Frodo%27s+Ring" in data["ligamagic_url"]
