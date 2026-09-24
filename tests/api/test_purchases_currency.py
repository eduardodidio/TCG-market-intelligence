"""Tests for USD -> BRL conversion in the purchases import-preview endpoint (F171-T08)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_current_user, get_db
from src.api.routers.purchases import _convert_item, router
from src.database.models import UserCollectionRow
from src.services.purchase_parser import ParsedPurchaseItem

_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
_TEST_USER_ID = 1


def _read_fixture(name: str) -> str:
    return (_FIXTURES_DIR / name).read_text(encoding="utf-8")


def _fake_user():
    user = MagicMock()
    user.id = _TEST_USER_ID
    return user


def _make_entry(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "user_id": str(_TEST_USER_ID),
        "card_id": 1,
        "set_code": "CMM",
        "collector_number": None,
        "name_en": "Sol Ring",
        "name_pt": None,
        "set_name_en": "Commander Masters",
        "quantity": 1,
        "quality": "NM",
        "language": "EN",
        "rarity": "U",
        "color": None,
        "extras": None,
        "acquisition_price": None,
        "acquired_at": None,
    }
    defaults.update(overrides)
    row = MagicMock(spec=UserCollectionRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_app(mock_repo: MagicMock) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[get_current_user] = _fake_user
    return app


def _sol_ring_and_command_tower_entries() -> list[MagicMock]:
    return [
        _make_entry(id=1, name_en="Sol Ring", set_code="CMM"),
        _make_entry(id=2, name_en="Command Tower", set_code="CMM", quantity=2),
    ]


class TestImportPreviewCurrencyConversion:
    def test_usd_item_converted_to_brl_with_rate(self):
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = _sol_ring_and_command_tower_entries()

        with patch(
            "src.services.currency.CurrencyConverter.get_display_rate",
            return_value=Decimal("5.00"),
        ):
            client = TestClient(_make_app(mock_repo))
            resp = client.post(
                "/api/v1/purchases/import-preview",
                files=[
                    (
                        "files",
                        (
                            "purchase_usd_sample.html",
                            _read_fixture("purchase_usd_sample.html"),
                            "text/html",
                        ),
                    )
                ],
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_items_matched"] == 2

        by_name = {m["card_name_parsed"]: m for m in data["matches"]}

        sol_ring = by_name["Sol Ring"]
        assert sol_ring["unit_price"] == "15.50"
        assert sol_ring["original_currency"] == "USD"
        assert sol_ring["original_unit_price"] == "3.10"
        assert sol_ring["exchange_rate"] == "5.00"

        command_tower = by_name["Command Tower"]
        assert command_tower["unit_price"] == "9.75"
        assert command_tower["original_currency"] == "BRL"
        assert command_tower["original_unit_price"] == "9.75"
        assert command_tower["exchange_rate"] is None

    def test_no_rate_excludes_usd_item_from_matches(self):
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = _sol_ring_and_command_tower_entries()

        with patch(
            "src.services.currency.CurrencyConverter.get_display_rate",
            return_value=None,
        ):
            client = TestClient(_make_app(mock_repo))
            resp = client.post(
                "/api/v1/purchases/import-preview",
                files=[
                    (
                        "files",
                        (
                            "purchase_usd_sample.html",
                            _read_fixture("purchase_usd_sample.html"),
                            "text/html",
                        ),
                    )
                ],
            )

        assert resp.status_code == 200
        data = resp.json()

        # BRL item still matches fine without a rate.
        assert data["total_items_matched"] == 1
        assert data["matches"][0]["card_name_parsed"] == "Command Tower"

        # USD item was moved out of matches into unmatched.
        assert data["total_items_unmatched"] == 1
        unmatched = data["unmatched"][0]
        assert unmatched["card_name_parsed"] == "Sol Ring"
        assert unmatched["skip_reason"] == "currency_conversion_failed"
        assert unmatched["original_currency"] == "USD"
        assert unmatched["original_unit_price"] == "3.10"

        assert any("Sol Ring" in w for w in data["warnings"])

    def test_eur_item_unsupported_currency_warning(self):
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = []

        item = ParsedPurchaseItem(
            card_name_pt=None,
            card_name_en="Some Euro Card",
            set_name=None,
            set_code=None,
            collector_number=None,
            language="EN",
            quality="NM",
            quantity=1,
            unit_price=Decimal("2.00"),
            is_foil=False,
            extras=[],
            order_number="1",
            order_date=date(2025, 1, 1),
            store_name="Test Store",
            source_file="x.html",
            currency="EUR",
        )
        brl_price, extra = _convert_item(item, lambda _d: Decimal("5.00"))
        assert brl_price is None
        assert extra["original_currency"] == "EUR"


class TestConvertItemHelper:
    def test_order_date_none_uses_today(self):
        item = ParsedPurchaseItem(
            card_name_pt=None,
            card_name_en="Sol Ring",
            set_name=None,
            set_code="CMM",
            collector_number=None,
            language="EN",
            quality="NM",
            quantity=1,
            unit_price=Decimal("3.10"),
            is_foil=False,
            extras=[],
            order_number="1",
            order_date=None,
            store_name="Test Store",
            source_file="x.html",
            currency="USD",
        )
        lookup = MagicMock(return_value=Decimal("5.00"))
        brl_price, extra = _convert_item(item, lookup)

        assert brl_price == "15.50"
        lookup.assert_called_once_with(date.today())

    def test_zero_price_usd_is_not_an_error(self):
        item = ParsedPurchaseItem(
            card_name_pt=None,
            card_name_en="Free Card",
            set_name=None,
            set_code=None,
            collector_number=None,
            language="EN",
            quality="NM",
            quantity=1,
            unit_price=Decimal("0"),
            is_foil=False,
            extras=[],
            order_number="1",
            order_date=date(2025, 1, 1),
            store_name="Test Store",
            source_file="x.html",
            currency="USD",
        )
        brl_price, extra = _convert_item(item, lambda _d: Decimal("5.00"))
        assert brl_price == "0.00"
        assert extra["original_currency"] == "USD"
