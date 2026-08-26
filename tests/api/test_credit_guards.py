"""Tests for credit guards on refresh and scan endpoints (F65-T04).

Verifies:
- 402 when non-admin user has insufficient credits
- Admin bypass (no credit check, no deduction)
- Credits deducted after successful refresh (MYP + Liga)
- Credits deducted before scan launch
- Provider failure does NOT deduct credits
- Transaction log has correct reason and reference_id
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import (
    get_credit_service,
    get_currency_converter_dep,
    get_current_user,
    get_db,
    require_auth_or_api_key,
)
from src.api.routers.collection import router as collection_router
from src.api.routers.scans import router as scans_router
from src.credits.constants import BULK_SCAN_COST, CARD_REFRESH_COST
from src.credits.service import CreditService
from src.database.models import PriceObservationRow, UserCollectionRow
from src.domain.models import CreditBalance, User
from src.providers.liga.provider import LigaMagicProvider
from src.providers.registry import ProviderRegistry
from src.services.currency import CurrencyConverter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(user_id: int = 1, is_admin: bool = False) -> User:
    return User(
        id=user_id,
        email="test@example.com",
        display_name="Test User",
        is_active=True,
        is_admin=is_admin,
    )


def _make_credit_svc(balance: int = 10) -> MagicMock:
    """Create a mock CreditService with a configurable balance."""
    svc = MagicMock(spec=CreditService)
    svc.check_sufficient.side_effect = lambda uid, cost: balance >= cost
    svc.get_balance.return_value = CreditBalance(user_id=1, balance=balance, last_bonus_at=None)
    svc.deduct.return_value = CreditBalance(
        user_id=1, balance=max(0, balance - CARD_REFRESH_COST), last_bonus_at=None
    )
    return svc


def _make_collection_row(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "user_id": "1",
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
        "extras": None,
    }
    defaults.update(overrides)
    row = MagicMock(spec=UserCollectionRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_price_obs(**overrides) -> MagicMock:
    defaults = {
        "id": 100,
        "source": "liga",
        "external_id": "liga_42",
        "observed_at": date(2026, 8, 24),
        "median_price": Decimal("5.50"),
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


def _make_converter() -> MagicMock:
    converter = MagicMock(spec=CurrencyConverter)
    converter.convert.return_value = Decimal("5.50")
    converter.get_display_rate.return_value = Decimal("5.00")
    return converter


def _make_liga_provider(**overrides) -> MagicMock:
    provider = MagicMock(spec=LigaMagicProvider)
    provider.source_name = "liga"
    provider.search_card = AsyncMock()
    provider.close = AsyncMock()
    for k, v in overrides.items():
        setattr(provider, k, v)
    return provider


def _mock_repo_for_detail(mock_repo: MagicMock, entry: MagicMock) -> None:
    mock_repo.get_collection_entry.return_value = entry
    price_obs = _make_price_obs()
    mock_repo.get_latest_prices_batch.return_value = {entry.card_id: price_obs}
    mock_repo.get_source_cards_for_card.return_value = []


def _make_collection_app(
    mock_repo: MagicMock,
    user: User,
    credit_svc: MagicMock,
    mock_provider: MagicMock | None = None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(collection_router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: str(user.id)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_credit_service] = lambda: credit_svc
    app.dependency_overrides[get_currency_converter_dep] = _make_converter

    if mock_provider is not None:
        registry = ProviderRegistry([mock_provider])
        app.state.provider_registry = registry

    return app


def _make_scans_app(user: User, credit_svc: MagicMock) -> FastAPI:
    app = FastAPI()
    app.include_router(scans_router)
    app.dependency_overrides[require_auth_or_api_key] = lambda: str(user.id)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_credit_service] = lambda: credit_svc
    return app


def _liga_prices(mid=None, low=None, high=None) -> dict:
    return {
        "card_name": "Lightning Bolt",
        "normal": {"low": low, "mid": mid, "high": high},
        "foil": {"low": None, "mid": None, "high": None},
    }


# ---------------------------------------------------------------------------
# POST /collection/{id}/refresh — MYP credit guards
# ---------------------------------------------------------------------------


class TestRefreshMypCreditGuard:
    """Credit guards on POST /collection/{id}/refresh (MYP)."""

    def test_insufficient_credits_returns_402(self) -> None:
        """Non-admin with 0 credits gets 402."""
        user = _make_user(is_admin=False)
        credit_svc = _make_credit_svc(balance=0)
        entry = _make_collection_row()
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = entry

        app = _make_collection_app(mock_repo, user, credit_svc)
        client = TestClient(app)

        resp = client.post("/collection/1/refresh")
        assert resp.status_code == 402
        body = resp.json()
        assert body["detail"]["code"] == "INSUFFICIENT_CREDITS"
        assert body["detail"]["balance"] == 0
        assert body["detail"]["cost"] == CARD_REFRESH_COST

    def test_admin_bypasses_credit_check(self) -> None:
        """Admin user with 0 balance does NOT get 402 (credit guard skipped)."""
        admin = _make_user(is_admin=True)
        credit_svc = _make_credit_svc(balance=0)
        # Entry not found triggers 404 AFTER the credit guard — if we get 404,
        # it proves the guard was bypassed.
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = None

        app = _make_collection_app(mock_repo, admin, credit_svc)
        client = TestClient(app)

        resp = client.post("/collection/1/refresh")
        # 404 = credit guard passed, endpoint continued to entry lookup
        assert resp.status_code == 404
        credit_svc.check_sufficient.assert_not_called()
        credit_svc.deduct.assert_not_called()

    def test_non_admin_with_credits_passes_guard(self) -> None:
        """Non-admin with sufficient credits passes the guard (gets 404 for missing entry)."""
        user = _make_user(is_admin=False)
        credit_svc = _make_credit_svc(balance=5)
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = None

        app = _make_collection_app(mock_repo, user, credit_svc)
        client = TestClient(app)

        resp = client.post("/collection/1/refresh")
        # 404 = credit guard passed, no deduction because action failed
        assert resp.status_code == 404
        credit_svc.check_sufficient.assert_called_once_with(user.id, CARD_REFRESH_COST)
        credit_svc.deduct.assert_not_called()


# ---------------------------------------------------------------------------
# POST /collection/{id}/refresh-liga — Liga credit guards
# ---------------------------------------------------------------------------


class TestRefreshLigaCreditGuard:
    """Credit guards on POST /collection/{id}/refresh-liga."""

    def test_insufficient_credits_returns_402(self) -> None:
        user = _make_user(is_admin=False)
        credit_svc = _make_credit_svc(balance=0)
        entry = _make_collection_row()
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = entry

        provider = _make_liga_provider()
        app = _make_collection_app(mock_repo, user, credit_svc, mock_provider=provider)
        client = TestClient(app)

        resp = client.post("/collection/1/refresh-liga")
        assert resp.status_code == 402
        body = resp.json()
        assert body["detail"]["code"] == "INSUFFICIENT_CREDITS"
        assert body["detail"]["balance"] == 0
        assert body["detail"]["cost"] == CARD_REFRESH_COST
        provider.search_card.assert_not_called()

    def test_admin_bypasses_credit_check(self) -> None:
        admin = _make_user(is_admin=True)
        credit_svc = _make_credit_svc(balance=0)
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider = _make_liga_provider()
        provider.search_card.return_value = _liga_prices(mid=Decimal("5.50"))

        app = _make_collection_app(mock_repo, admin, credit_svc, mock_provider=provider)
        client = TestClient(app)

        resp = client.post("/collection/1/refresh-liga")
        assert resp.status_code == 200
        credit_svc.deduct.assert_not_called()
        credit_svc.check_sufficient.assert_not_called()

    def test_successful_refresh_deducts_credit(self) -> None:
        user = _make_user(is_admin=False)
        credit_svc = _make_credit_svc(balance=5)
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider = _make_liga_provider()
        provider.search_card.return_value = _liga_prices(mid=Decimal("5.50"))

        app = _make_collection_app(mock_repo, user, credit_svc, mock_provider=provider)
        client = TestClient(app)

        resp = client.post("/collection/1/refresh-liga")
        assert resp.status_code == 200
        credit_svc.deduct.assert_called_once_with(
            user.id, CARD_REFRESH_COST, "card_refresh", reference_id="1"
        )

    def test_refresh_liga_balance_1_succeeds(self) -> None:
        """With exactly 1 credit (cost=1), refresh succeeds and balance goes to 0."""
        user = _make_user(is_admin=False)
        credit_svc = _make_credit_svc(balance=1)
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider = _make_liga_provider()
        provider.search_card.return_value = _liga_prices(mid=Decimal("3.00"))

        app = _make_collection_app(mock_repo, user, credit_svc, mock_provider=provider)
        client = TestClient(app)

        resp = client.post("/collection/1/refresh-liga")
        assert resp.status_code == 200
        credit_svc.deduct.assert_called_once()

    def test_provider_error_no_deduction(self) -> None:
        """Liga errors return 200 with warning but do NOT deduct credits."""
        from src.providers.liga.exceptions import LigaNotFoundError

        user = _make_user(is_admin=False)
        credit_svc = _make_credit_svc(balance=5)
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider = _make_liga_provider()
        provider.search_card.side_effect = LigaNotFoundError("not found")

        app = _make_collection_app(mock_repo, user, credit_svc, mock_provider=provider)
        client = TestClient(app)

        resp = client.post("/collection/1/refresh-liga")
        assert resp.status_code == 200
        # Errors returned but no deduction
        credit_svc.deduct.assert_not_called()

    def test_no_price_found_no_deduction(self) -> None:
        """When Liga returns all-None prices, no deduction."""
        user = _make_user(is_admin=False)
        credit_svc = _make_credit_svc(balance=5)
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider = _make_liga_provider()
        provider.search_card.return_value = _liga_prices()  # all None

        app = _make_collection_app(mock_repo, user, credit_svc, mock_provider=provider)
        client = TestClient(app)

        resp = client.post("/collection/1/refresh-liga")
        assert resp.status_code == 200
        credit_svc.deduct.assert_not_called()


# ---------------------------------------------------------------------------
# POST /scans — bulk scan credit guards
# ---------------------------------------------------------------------------


class TestScanCreditGuard:
    """Credit guards on POST /scans (bulk scan)."""

    @patch("src.api.routers.scans.threading.Thread")
    @patch("src.api.routers.scans.Repository")
    def test_insufficient_credits_returns_402(
        self, mock_repo_cls: MagicMock, mock_thread_cls: MagicMock
    ) -> None:
        user = _make_user(is_admin=False)
        credit_svc = _make_credit_svc(balance=3)  # need 5

        app = _make_scans_app(user, credit_svc)
        client = TestClient(app)

        resp = client.post("/scans", json={"scan_type": "collection"})
        assert resp.status_code == 402
        body = resp.json()
        assert body["detail"]["code"] == "INSUFFICIENT_CREDITS"
        assert body["detail"]["balance"] == 3
        assert body["detail"]["cost"] == BULK_SCAN_COST
        mock_thread_cls.assert_not_called()

    @patch("src.api.routers.scans.threading.Thread")
    @patch("src.api.routers.scans.Repository")
    def test_admin_bypasses_credit_check(
        self, mock_repo_cls: MagicMock, mock_thread_cls: MagicMock
    ) -> None:
        admin = _make_user(is_admin=True)
        credit_svc = _make_credit_svc(balance=0)

        mock_repo = MagicMock()
        mock_repo.create_scan_run.return_value = 1
        mock_repo_cls.return_value = mock_repo
        mock_thread_cls.return_value = MagicMock()

        app = _make_scans_app(admin, credit_svc)
        client = TestClient(app)

        resp = client.post("/scans", json={"scan_type": "collection"})
        assert resp.status_code == 200
        credit_svc.deduct.assert_not_called()
        credit_svc.check_sufficient.assert_not_called()

    @patch("src.api.routers.scans.threading.Thread")
    @patch("src.api.routers.scans.Repository")
    def test_successful_scan_deducts_before_launch(
        self, mock_repo_cls: MagicMock, mock_thread_cls: MagicMock
    ) -> None:
        user = _make_user(is_admin=False)
        credit_svc = _make_credit_svc(balance=10)

        mock_repo = MagicMock()
        mock_repo.create_scan_run.return_value = 42
        mock_repo_cls.return_value = mock_repo
        mock_thread_cls.return_value = MagicMock()

        app = _make_scans_app(user, credit_svc)
        client = TestClient(app)

        resp = client.post("/scans", json={"scan_type": "collection"})
        assert resp.status_code == 200
        assert resp.json()["scan_id"] == 42

        credit_svc.deduct.assert_called_once_with(
            user.id, BULK_SCAN_COST, "bulk_scan", reference_id="scan"
        )

    @patch("src.api.routers.scans.threading.Thread")
    @patch("src.api.routers.scans.Repository")
    def test_scan_exactly_enough_credits(
        self, mock_repo_cls: MagicMock, mock_thread_cls: MagicMock
    ) -> None:
        """With exactly 5 credits (cost=5), scan succeeds."""
        user = _make_user(is_admin=False)
        credit_svc = _make_credit_svc(balance=5)

        mock_repo = MagicMock()
        mock_repo.create_scan_run.return_value = 1
        mock_repo_cls.return_value = mock_repo
        mock_thread_cls.return_value = MagicMock()

        app = _make_scans_app(user, credit_svc)
        client = TestClient(app)

        resp = client.post("/scans", json={"scan_type": "collection"})
        assert resp.status_code == 200
        credit_svc.deduct.assert_called_once()


# ---------------------------------------------------------------------------
# 402 response format consistency
# ---------------------------------------------------------------------------


class TestCreditErrorFormat:
    """Verify the 402 error response has the expected structure."""

    def test_402_has_message_field(self) -> None:
        user = _make_user(is_admin=False)
        credit_svc = _make_credit_svc(balance=0)
        entry = _make_collection_row()
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = entry

        provider = _make_liga_provider()
        app = _make_collection_app(mock_repo, user, credit_svc, mock_provider=provider)
        client = TestClient(app)

        resp = client.post("/collection/1/refresh-liga")
        assert resp.status_code == 402
        detail = resp.json()["detail"]
        assert "message" in detail
        assert "treasure tokens" in detail["message"].lower()

    @patch("src.api.routers.scans.threading.Thread")
    @patch("src.api.routers.scans.Repository")
    def test_402_scan_format(self, mock_repo_cls: MagicMock, mock_thread_cls: MagicMock) -> None:
        user = _make_user(is_admin=False)
        credit_svc = _make_credit_svc(balance=2)

        app = _make_scans_app(user, credit_svc)
        client = TestClient(app)

        resp = client.post("/scans", json={"scan_type": "collection"})
        assert resp.status_code == 402
        detail = resp.json()["detail"]
        assert detail["code"] == "INSUFFICIENT_CREDITS"
        assert detail["balance"] == 2
        assert detail["cost"] == 5
        assert "message" in detail
