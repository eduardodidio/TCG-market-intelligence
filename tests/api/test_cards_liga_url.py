"""Tests for CardDetail endpoint using resolve_liga_card_url.

Verifies that the endpoint prefers stored Liga URLs from the database
and falls back to name-based URLs when no stored URL exists.
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


class TestCardDetailResolveLigaUrl:
    """CardDetail should prefer stored Liga URLs over name-based ones."""

    def test_card_detail_uses_stored_liga_url(self) -> None:
        """When a stored Liga URL exists, it should be returned."""
        stored_url = "https://www.ligamagic.com.br/?view=cards/card&card=Lightning+Bolt&ed=dmr"
        mock_repo = MagicMock()
        mock_repo.get_card_by_id.return_value = _make_card_row(id=42)
        mock_repo.get_source_cards_for_card.return_value = []
        mock_repo.get_latest_prices_batch.return_value = {}
        mock_repo.get_liga_card_url.return_value = stored_url

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/cards/42")
        data = resp.json()["data"]

        assert data["ligamagic_url"] == stored_url
        # Verify get_liga_card_url was called with the correct external_id
        mock_repo.get_liga_card_url.assert_called_with("liga_42")

    def test_card_detail_falls_back_to_name_url(self) -> None:
        """When no stored Liga URL exists, fall back to name-based URL."""
        mock_repo = MagicMock()
        mock_repo.get_card_by_id.return_value = _make_card_row(
            id=7,
            name_en="Counterspell",
        )
        mock_repo.get_source_cards_for_card.return_value = []
        mock_repo.get_latest_prices_batch.return_value = {}
        mock_repo.get_liga_card_url.return_value = None

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/cards/7")
        data = resp.json()["data"]

        assert data["ligamagic_url"] is not None
        assert "Counterspell" in data["ligamagic_url"]
        assert "view=cards/card" in data["ligamagic_url"]

    def test_card_detail_liga_url_none_when_no_name(self) -> None:
        """resolve_liga_card_url returns None when fallback_name is empty
        and no stored URL exists. We test the resolver directly because
        the CardDetail schema requires name_en to be a non-null string.
        """
        from src.providers.liga.urls import resolve_liga_card_url

        result = resolve_liga_card_url(
            card_id=99,
            is_foil=False,
            fallback_name="",
            lookup=lambda _ext_id: None,
        )
        assert result is None
