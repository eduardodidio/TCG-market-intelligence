"""Tests for POST /collection/{entry_id}/canonize — error handling."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.database.models import UserCollectionRow

_TEST_USER_ID = "eduardo"

# Patch targets — canonize uses inline imports from these modules
_PATCH_PROVIDER = "src.providers.myp.provider.MypCardsProvider"
_PATCH_MATCHER = "src.collection.matcher.match_collection_card"
_PATCH_CONVERTER = "src.collection.converter.row_to_collection_entry"


def _make_collection_row(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "user_id": _TEST_USER_ID,
        "card_id": None,
        "set_code": "DMR",
        "collector_number": "123",
        "name_en": "Lightning Bolt",
        "name_pt": "Raio",
        "set_name_en": "Dominaria Remastered",
        "quantity": 1,
        "quality": "NM",
        "language": "EN",
        "rarity": "R",
        "color": "R",
        "extras": None,
        "created_at": datetime(2026, 1, 1),
    }
    defaults.update(overrides)
    row = MagicMock(spec=UserCollectionRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_app(mock_repo: MagicMock, user_id: str = _TEST_USER_ID) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: user_id
    return app


def _make_collection_entry_mock():
    """Mock return value for row_to_collection_entry."""
    ce = MagicMock()
    ce.name_en = "Lightning Bolt"
    ce.name_pt = "Raio"
    return ce


class TestCanonizeErrorHandling:
    """POST /collection/{entry_id}/canonize — MYP failure scenarios."""

    def test_returns_404_for_nonexistent_entry(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = None

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.post("/collection/999/canonize")
        assert resp.status_code == 404

    def test_returns_422_when_already_canonical_with_source(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row(card_id=42)
        myp_source = MagicMock()
        myp_source.source = "myp"
        mock_repo.get_source_cards_for_card.return_value = [myp_source]

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.post("/collection/1/canonize")
        assert resp.status_code == 422

    @patch(_PATCH_PROVIDER)
    @patch(_PATCH_MATCHER)
    @patch(_PATCH_CONVERTER)
    def test_recanonize_orphan_card_without_source(
        self, mock_converter, mock_match, mock_provider_cls
    ) -> None:
        """When card_id exists but has no MYP source cards, re-run search."""
        mock_repo = MagicMock()
        orphan_row = _make_collection_row(card_id=42)
        mock_repo.get_collection_entry.side_effect = [orphan_row, orphan_row]
        mock_repo.get_source_cards_for_card.return_value = []  # no source cards
        mock_repo.get_latest_prices_batch.return_value = {}

        mock_converter.return_value = _make_collection_entry_mock()

        mock_match_result = MagicMock()
        mock_match_result.status = "no_match"
        mock_match_result.myp_result = None
        mock_match.return_value = mock_match_result

        mock_provider = AsyncMock()
        mock_provider.search_card.return_value = []
        mock_provider.close = AsyncMock()
        mock_provider_cls.return_value = mock_provider

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.post("/collection/1/canonize")
        assert resp.status_code == 200
        # Should NOT create a new CardRow
        mock_repo.create_canonical_card.assert_not_called()
        mock_repo.link_collection_entry.assert_not_called()

    @patch(_PATCH_PROVIDER)
    @patch(_PATCH_MATCHER)
    @patch(_PATCH_CONVERTER)
    def test_search_card_failure_returns_success_with_warning(
        self, mock_converter, mock_match, mock_provider_cls
    ) -> None:
        """When provider.search_card raises, card should still be linked
        and response should include a warning error."""
        mock_repo = MagicMock()
        unlinked_row = _make_collection_row(card_id=None)
        linked_row = _make_collection_row(card_id=100)
        mock_repo.get_collection_entry.side_effect = [unlinked_row, linked_row]
        mock_repo.create_canonical_card.return_value = 100
        mock_repo.get_latest_prices_batch.return_value = {}
        mock_repo.get_source_cards_for_card.return_value = []

        mock_converter.return_value = _make_collection_entry_mock()

        mock_provider = AsyncMock()
        mock_provider.search_card.side_effect = RuntimeError("MYP timeout")
        mock_provider.close = AsyncMock()
        mock_provider_cls.return_value = mock_provider

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.post("/collection/1/canonize")
        assert resp.status_code == 200

        body = resp.json()
        assert body["data"] is not None
        assert body["data"]["card_id"] == 100
        assert len(body["errors"]) == 1
        assert body["errors"][0]["code"] == "myp_fetch_warning"
        assert "MYP timeout" in body["errors"][0]["message"]

        # Card was still linked
        mock_repo.create_canonical_card.assert_called_once()
        mock_repo.link_collection_entry.assert_called_once_with(1, 100)

    @patch(_PATCH_PROVIDER)
    @patch(_PATCH_MATCHER)
    @patch(_PATCH_CONVERTER)
    def test_get_card_details_failure_returns_success_with_warning(
        self, mock_converter, mock_match, mock_provider_cls
    ) -> None:
        """When provider.get_card_details raises after a match, card should
        still be linked with a warning."""
        mock_repo = MagicMock()
        unlinked_row = _make_collection_row(card_id=None)
        linked_row = _make_collection_row(card_id=100)
        mock_repo.get_collection_entry.side_effect = [unlinked_row, linked_row]
        mock_repo.create_canonical_card.return_value = 100
        mock_repo.get_latest_prices_batch.return_value = {}
        mock_repo.get_source_cards_for_card.return_value = []

        mock_converter.return_value = _make_collection_entry_mock()

        # Match succeeds but get_card_details raises
        mock_match_result = MagicMock()
        mock_match_result.status = "matched"
        mock_myp = MagicMock()
        mock_myp.external_id = "12345"
        mock_myp.url = "https://mypcards.com/magic/12345/lightning-bolt"
        mock_myp.sku = "magic_dmr_123"
        mock_match_result.myp_result = mock_myp
        mock_match.return_value = mock_match_result

        mock_provider = AsyncMock()
        mock_provider.search_card.return_value = [MagicMock()]
        mock_provider.get_card_details.side_effect = ConnectionError("Network error")
        mock_provider.close = AsyncMock()
        mock_provider_cls.return_value = mock_provider

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.post("/collection/1/canonize")
        assert resp.status_code == 200

        body = resp.json()
        assert body["data"] is not None
        assert len(body["errors"]) == 1
        assert body["errors"][0]["code"] == "myp_fetch_warning"
        assert "Network error" in body["errors"][0]["message"]

    @patch(_PATCH_PROVIDER)
    @patch(_PATCH_MATCHER)
    @patch(_PATCH_CONVERTER)
    def test_happy_path_no_warnings(self, mock_converter, mock_match, mock_provider_cls) -> None:
        """Happy path: no MYP errors, no warnings in response."""
        mock_repo = MagicMock()
        unlinked_row = _make_collection_row(card_id=None)
        linked_row = _make_collection_row(card_id=100)
        mock_repo.get_collection_entry.side_effect = [unlinked_row, linked_row]
        mock_repo.create_canonical_card.return_value = 100
        mock_repo.get_latest_prices_batch.return_value = {}
        mock_repo.get_source_cards_for_card.return_value = []

        mock_converter.return_value = _make_collection_entry_mock()

        # No match — no MYP interaction beyond search
        mock_match_result = MagicMock()
        mock_match_result.status = "no_match"
        mock_match_result.myp_result = None
        mock_match.return_value = mock_match_result

        mock_provider = AsyncMock()
        mock_provider.search_card.return_value = []
        mock_provider.close = AsyncMock()
        mock_provider_cls.return_value = mock_provider

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.post("/collection/1/canonize")
        assert resp.status_code == 200

        body = resp.json()
        assert body["data"] is not None
        assert body["errors"] == []

    @patch(_PATCH_PROVIDER)
    @patch(_PATCH_MATCHER)
    @patch(_PATCH_CONVERTER)
    def test_provider_close_called_even_on_failure(
        self, mock_converter, mock_match, mock_provider_cls
    ) -> None:
        """Provider.close() is called even when an exception occurs."""
        mock_repo = MagicMock()
        unlinked_row = _make_collection_row(card_id=None)
        linked_row = _make_collection_row(card_id=100)
        mock_repo.get_collection_entry.side_effect = [unlinked_row, linked_row]
        mock_repo.create_canonical_card.return_value = 100
        mock_repo.get_latest_prices_batch.return_value = {}
        mock_repo.get_source_cards_for_card.return_value = []

        mock_converter.return_value = _make_collection_entry_mock()

        mock_provider = AsyncMock()
        mock_provider.search_card.side_effect = RuntimeError("boom")
        mock_provider.close = AsyncMock()
        mock_provider_cls.return_value = mock_provider

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.post("/collection/1/canonize")
        assert resp.status_code == 200

        mock_provider.close.assert_awaited_once()

    @patch(_PATCH_PROVIDER)
    @patch(_PATCH_MATCHER)
    @patch(_PATCH_CONVERTER)
    def test_pt_fallback_when_en_returns_no_results(
        self, mock_converter, mock_match, mock_provider_cls
    ) -> None:
        """When EN search returns empty, retries with PT name."""
        mock_repo = MagicMock()
        unlinked_row = _make_collection_row(card_id=None)
        linked_row = _make_collection_row(card_id=100)
        mock_repo.get_collection_entry.side_effect = [unlinked_row, linked_row]
        mock_repo.create_canonical_card.return_value = 100
        mock_repo.get_latest_prices_batch.return_value = {}
        mock_repo.get_source_cards_for_card.return_value = []

        ce = _make_collection_entry_mock()
        ce.name_en = "Abrade"
        ce.name_pt = "Abrasão"
        mock_converter.return_value = ce

        mock_match_result = MagicMock()
        mock_match_result.status = "no_match"
        mock_match_result.myp_result = None
        mock_match.return_value = mock_match_result

        mock_provider = AsyncMock()
        # EN search returns empty, PT search returns results
        mock_provider.search_card.side_effect = [[], [MagicMock()]]
        mock_provider.close = AsyncMock()
        mock_provider_cls.return_value = mock_provider

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.post("/collection/1/canonize")
        assert resp.status_code == 200

        # Should have called search_card twice: EN then PT
        assert mock_provider.search_card.call_count == 2
        mock_provider.search_card.assert_any_call("Abrade")
        mock_provider.search_card.assert_any_call("Abrasão")
