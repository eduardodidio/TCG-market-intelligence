"""Integration tests for PATCH /collection/{entry_id}/price — manual price endpoint."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_currency_converter_dep, get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.database.models import PriceObservationRow, UserCollectionRow
from src.services.currency import CurrencyConverter

_TEST_USER_ID = "eduardo"


def _make_collection_row(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "user_id": _TEST_USER_ID,
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
    }
    defaults.update(overrides)
    row = MagicMock(spec=UserCollectionRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_price_obs(**overrides) -> MagicMock:
    defaults = {
        "id": 100,
        "source": "manual",
        "external_id": "manual_1",
        "observed_at": date(2026, 8, 22),
        "median_price": Decimal("10.50"),
        "tcg_price": None,
        "last_sold_price": None,
        "quantity_available": None,
        "last_sold_meta": None,
        "currency": "BRL",
    }
    defaults.update(overrides)
    obs = MagicMock(spec=PriceObservationRow)
    for k, v in defaults.items():
        setattr(obs, k, v)
    return obs


def _make_app(
    mock_repo: MagicMock,
    mock_converter: MagicMock | None = None,
    user_id: str = _TEST_USER_ID,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: user_id
    if mock_converter is not None:
        app.dependency_overrides[get_currency_converter_dep] = lambda: mock_converter
    else:
        converter = MagicMock(spec=CurrencyConverter)
        converter.convert.return_value = Decimal("10.50")
        converter.get_display_rate.return_value = Decimal("5.00")
        app.dependency_overrides[get_currency_converter_dep] = lambda: converter
    return app


class TestManualPriceEndpointAuth:
    """Auth and IDOR checks for PATCH /collection/{id}/price."""

    def test_auth_required(self) -> None:
        """Without auth override, endpoint should require authentication."""
        mock_repo = MagicMock()
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: mock_repo
        # Do NOT override require_auth_or_api_key — it should fail
        # But since TestClient doesn't actually send real auth,
        # we test by setting user_id override to raise
        from fastapi import HTTPException

        def deny_auth():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[require_auth_or_api_key] = deny_auth
        converter = MagicMock(spec=CurrencyConverter)
        converter.convert.return_value = Decimal("10.50")
        app.dependency_overrides[get_currency_converter_dep] = lambda: converter
        client = TestClient(app)

        resp = client.patch("/collection/1/price", json={"price": 10.0})
        assert resp.status_code == 401

    def test_idor_check(self) -> None:
        """Entry belonging to a different user returns 403."""
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row(user_id="other_user")

        app = _make_app(mock_repo, user_id=_TEST_USER_ID)
        client = TestClient(app)

        resp = client.patch("/collection/1/price", json={"price": 10.0})
        assert resp.status_code == 403

    def test_404_nonexistent(self) -> None:
        """Nonexistent entry returns 404."""
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = None

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.patch("/collection/999/price", json={"price": 10.0})
        assert resp.status_code == 404


class TestManualPriceEndpointValidation:
    """Input validation for PATCH /collection/{id}/price."""

    def test_validates_negative_price(self) -> None:
        mock_repo = MagicMock()
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.patch("/collection/1/price", json={"price": -5.0})
        assert resp.status_code == 422

    def test_validates_zero_price(self) -> None:
        mock_repo = MagicMock()
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.patch("/collection/1/price", json={"price": 0.0})
        assert resp.status_code == 422

    def test_validates_price_exceeds_max(self) -> None:
        mock_repo = MagicMock()
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.patch("/collection/1/price", json={"price": 100000.0})
        assert resp.status_code == 422

    def test_validates_invalid_currency(self) -> None:
        mock_repo = MagicMock()
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.patch("/collection/1/price", json={"price": 10.0, "currency": "EUR"})
        assert resp.status_code == 422


class TestManualPriceEndpointHappyPath:
    """Happy path for PATCH /collection/{id}/price."""

    def test_creates_manual_price_and_returns_detail(self) -> None:
        mock_repo = MagicMock()
        entry = _make_collection_row()
        # get_collection_entry called in set_manual_price + _build_collection_detail
        mock_repo.get_collection_entry.return_value = entry
        mock_repo.upsert_manual_price.return_value = 100
        price_obs = _make_price_obs()
        mock_repo.get_latest_prices_batch.return_value = {42: price_obs}
        mock_repo.get_source_cards_for_card.return_value = []

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.patch("/collection/1/price", json={"price": 10.50})
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["id"] == 1
        assert data["name_en"] == "Lightning Bolt"

        # Verify upsert was called
        mock_repo.upsert_manual_price.assert_called_once()
        call_args = mock_repo.upsert_manual_price.call_args
        assert call_args[0][0] == 42  # card_id
        assert call_args[0][1] == Decimal("10.50")  # price_brl

    def test_converts_usd_to_brl(self) -> None:
        mock_repo = MagicMock()
        entry = _make_collection_row()
        mock_repo.get_collection_entry.return_value = entry
        mock_repo.upsert_manual_price.return_value = 100
        mock_repo.get_latest_prices_batch.return_value = {42: _make_price_obs()}
        mock_repo.get_source_cards_for_card.return_value = []

        converter = MagicMock(spec=CurrencyConverter)
        converter.get_display_rate.return_value = Decimal("5.00")
        converter.convert.return_value = Decimal("50.00")

        app = _make_app(mock_repo, mock_converter=converter)
        client = TestClient(app)

        resp = client.patch(
            "/collection/1/price",
            json={"price": 10.0, "currency": "USD"},
        )
        assert resp.status_code == 200

        # Verify BRL conversion: 10 USD * 5.00 = 50.00 BRL
        call_args = mock_repo.upsert_manual_price.call_args
        assert call_args[0][1] == Decimal("50.00")

    def test_pila_stored_as_brl(self) -> None:
        """PILA is 1:1 with BRL, so no conversion needed."""
        mock_repo = MagicMock()
        entry = _make_collection_row()
        mock_repo.get_collection_entry.return_value = entry
        mock_repo.upsert_manual_price.return_value = 100
        mock_repo.get_latest_prices_batch.return_value = {42: _make_price_obs()}
        mock_repo.get_source_cards_for_card.return_value = []

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.patch(
            "/collection/1/price",
            json={"price": 25.00, "currency": "PILA"},
        )
        assert resp.status_code == 200

        call_args = mock_repo.upsert_manual_price.call_args
        assert call_args[0][1] == Decimal("25.00")

    def test_usd_conversion_fails_without_rate(self) -> None:
        """When exchange rate is unavailable, returns 422."""
        mock_repo = MagicMock()
        entry = _make_collection_row()
        mock_repo.get_collection_entry.return_value = entry

        converter = MagicMock(spec=CurrencyConverter)
        converter.get_display_rate.return_value = None

        app = _make_app(mock_repo, mock_converter=converter)
        client = TestClient(app)

        resp = client.patch(
            "/collection/1/price",
            json={"price": 10.0, "currency": "USD"},
        )
        assert resp.status_code == 422
        assert "Exchange rate" in resp.json()["detail"]


class TestManualPriceAutoCreateCard:
    """Auto-creation of CardRow for unlinked entries."""

    def test_auto_creates_card_for_unlinked_entry(self) -> None:
        mock_repo = MagicMock()
        entry = _make_collection_row(card_id=None)
        # After linking, subsequent get_collection_entry calls return with card_id
        linked_entry = _make_collection_row(card_id=99)
        mock_repo.get_collection_entry.side_effect = [entry, linked_entry, linked_entry]
        mock_repo.create_canonical_card.return_value = 99
        mock_repo.upsert_manual_price.return_value = 100
        mock_repo.get_latest_prices_batch.return_value = {99: _make_price_obs()}
        mock_repo.get_source_cards_for_card.return_value = []

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.patch("/collection/1/price", json={"price": 15.00})
        assert resp.status_code == 200

        # Verify card was created
        mock_repo.create_canonical_card.assert_called_once_with(
            game="magic",
            name_en="Lightning Bolt",
            name_pt="Raio",
            set_code="DMR",
            collector_number="123",
        )
        # Verify entry was linked
        mock_repo.link_collection_entry.assert_called_once_with(1, 99)

    def test_does_not_create_card_for_linked_entry(self) -> None:
        mock_repo = MagicMock()
        entry = _make_collection_row(card_id=42)
        mock_repo.get_collection_entry.return_value = entry
        mock_repo.upsert_manual_price.return_value = 100
        mock_repo.get_latest_prices_batch.return_value = {42: _make_price_obs()}
        mock_repo.get_source_cards_for_card.return_value = []

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.patch("/collection/1/price", json={"price": 15.00})
        assert resp.status_code == 200

        mock_repo.create_canonical_card.assert_not_called()
        mock_repo.link_collection_entry.assert_not_called()
