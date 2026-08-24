"""Tests for ProviderRegistry and create_registry_from_env."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.interfaces import CardSourceProvider
from src.domain.models import HistoricalPrice, PriceSnapshot, SourceCard
from src.providers.registry import ProviderRegistry, create_registry_from_env

# --- Helpers ---


def _make_card(external_id: str = "123") -> SourceCard:
    return SourceCard(source="test", external_id=external_id, url="http://x")


def _make_snapshot(source: str = "test", price: Decimal = Decimal("10.00")) -> PriceSnapshot:
    return PriceSnapshot(
        source=source,
        external_id="123",
        observed_at=datetime.now(),
        min_price=price,
        avg_price=price,
        currency="BRL",
    )


def _make_provider(
    name: str,
    price: PriceSnapshot | None = None,
    price_error: Exception | None = None,
    sets: list[str] | None = None,
    sets_error: Exception | None = None,
    cards: list[SourceCard] | None = None,
    cards_error: Exception | None = None,
    history: list[HistoricalPrice] | None = None,
    history_error: Exception | None = None,
) -> CardSourceProvider:
    """Build a mock CardSourceProvider."""
    provider = MagicMock(spec=CardSourceProvider)
    provider.source_name = name

    if price_error:
        provider.get_current_price = AsyncMock(side_effect=price_error)
    else:
        provider.get_current_price = AsyncMock(return_value=price)

    if sets_error:
        provider.discover_sets = AsyncMock(side_effect=sets_error)
    else:
        provider.discover_sets = AsyncMock(return_value=sets or [])

    if cards_error:
        provider.discover_cards = AsyncMock(side_effect=cards_error)
    else:
        provider.discover_cards = AsyncMock(return_value=cards or [])

    if history_error:
        provider.get_price_history = AsyncMock(side_effect=history_error)
    else:
        provider.get_price_history = AsyncMock(return_value=history or [])

    return provider


# --- ProviderRegistry ---


class TestProviderRegistry:
    def test_source_names(self):
        p1 = _make_provider("liga")
        p2 = _make_provider("myp")
        registry = ProviderRegistry([p1, p2])
        assert registry.source_names == ["liga", "myp"]

    def test_source_names_empty(self):
        registry = ProviderRegistry([])
        assert registry.source_names == []


class TestGetCurrentPrice:
    @pytest.mark.asyncio
    async def test_first_provider_succeeds(self):
        snap = _make_snapshot("liga")
        p1 = _make_provider("liga", price=snap)
        p2 = _make_provider("myp", price=_make_snapshot("myp"))
        registry = ProviderRegistry([p1, p2])

        result = await registry.get_current_price(_make_card())

        assert result is snap
        p1.get_current_price.assert_awaited_once()
        p2.get_current_price.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_fallback_on_error(self):
        """First provider raises, second returns a price."""
        p1 = _make_provider("liga", price_error=RuntimeError("browser crashed"))
        snap = _make_snapshot("myp")
        p2 = _make_provider("myp", price=snap)
        registry = ProviderRegistry([p1, p2])

        result = await registry.get_current_price(_make_card())

        assert result is snap
        p1.get_current_price.assert_awaited_once()
        p2.get_current_price.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fallback_on_none(self):
        """First provider returns None, second returns a price."""
        p1 = _make_provider("liga", price=None)
        snap = _make_snapshot("myp")
        p2 = _make_provider("myp", price=snap)
        registry = ProviderRegistry([p1, p2])

        result = await registry.get_current_price(_make_card())

        assert result is snap

    @pytest.mark.asyncio
    async def test_all_providers_fail(self):
        p1 = _make_provider("liga", price_error=RuntimeError("fail"))
        p2 = _make_provider("myp", price_error=RuntimeError("fail"))
        registry = ProviderRegistry([p1, p2])

        result = await registry.get_current_price(_make_card())

        assert result is None

    @pytest.mark.asyncio
    async def test_all_providers_return_none(self):
        p1 = _make_provider("liga", price=None)
        p2 = _make_provider("myp", price=None)
        registry = ProviderRegistry([p1, p2])

        result = await registry.get_current_price(_make_card())

        assert result is None

    @pytest.mark.asyncio
    async def test_empty_registry(self):
        registry = ProviderRegistry([])

        result = await registry.get_current_price(_make_card())

        assert result is None


class TestGetPriceHistory:
    @pytest.mark.asyncio
    async def test_first_provider_returns_history(self):
        h = [HistoricalPrice(source="liga", external_id="1", observed_at=datetime.now().date())]
        p1 = _make_provider("liga", history=h)
        p2 = _make_provider("myp")
        registry = ProviderRegistry([p1, p2])

        result = await registry.get_price_history(_make_card())

        assert result == h
        p2.get_price_history.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_fallback_on_empty_history(self):
        h = [HistoricalPrice(source="myp", external_id="1", observed_at=datetime.now().date())]
        p1 = _make_provider("liga", history=[])
        p2 = _make_provider("myp", history=h)
        registry = ProviderRegistry([p1, p2])

        result = await registry.get_price_history(_make_card())

        assert result == h

    @pytest.mark.asyncio
    async def test_all_fail_returns_empty(self):
        p1 = _make_provider("liga", history_error=RuntimeError("fail"))
        p2 = _make_provider("myp", history_error=RuntimeError("fail"))
        registry = ProviderRegistry([p1, p2])

        result = await registry.get_price_history(_make_card())

        assert result == []


class TestDiscoverSets:
    @pytest.mark.asyncio
    async def test_aggregation(self):
        p1 = _make_provider("liga", sets=["SET_A", "SET_B"])
        p2 = _make_provider("myp", sets=["SET_B", "SET_C"])
        registry = ProviderRegistry([p1, p2])

        result = await registry.discover_sets()

        assert result == ["SET_A", "SET_B", "SET_C"]

    @pytest.mark.asyncio
    async def test_one_provider_errors(self):
        p1 = _make_provider("liga", sets_error=RuntimeError("fail"))
        p2 = _make_provider("myp", sets=["SET_X"])
        registry = ProviderRegistry([p1, p2])

        result = await registry.discover_sets()

        assert result == ["SET_X"]

    @pytest.mark.asyncio
    async def test_empty_registry(self):
        registry = ProviderRegistry([])

        result = await registry.discover_sets()

        assert result == []


class TestDiscoverCards:
    @pytest.mark.asyncio
    async def test_first_succeeds(self):
        cards = [_make_card("1")]
        p1 = _make_provider("liga", cards=cards)
        p2 = _make_provider("myp", cards=[_make_card("2")])
        registry = ProviderRegistry([p1, p2])

        result = await registry.discover_cards("some_set")

        assert result == cards
        p2.discover_cards.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_fallback_on_empty(self):
        cards = [_make_card("2")]
        p1 = _make_provider("liga", cards=[])
        p2 = _make_provider("myp", cards=cards)
        registry = ProviderRegistry([p1, p2])

        result = await registry.discover_cards("some_set")

        assert result == cards

    @pytest.mark.asyncio
    async def test_all_empty(self):
        p1 = _make_provider("liga", cards=[])
        p2 = _make_provider("myp", cards=[])
        registry = ProviderRegistry([p1, p2])

        result = await registry.discover_cards()

        assert result == []

    @pytest.mark.asyncio
    async def test_fallback_on_error(self):
        cards = [_make_card("2")]
        p1 = _make_provider("liga", cards_error=RuntimeError("fail"))
        p2 = _make_provider("myp", cards=cards)
        registry = ProviderRegistry([p1, p2])

        result = await registry.discover_cards()

        assert result == cards


# --- create_registry_from_env ---


class TestCreateRegistryFromEnv:
    @patch.dict("os.environ", {"TCG_PROVIDER_ORDER": "liga,myp"}, clear=False)
    @patch("src.providers.registry.log")
    def test_default_order_liga_myp(self, _mock_log):
        with (
            patch("src.providers.liga.provider.LigaMagicProvider") as MockLiga,
            patch("src.providers.myp.provider.MypCardsProvider") as MockMyp,
        ):
            MockLiga.return_value = MagicMock(source_name="liga")
            MockMyp.return_value = MagicMock(source_name="myp")

            registry = create_registry_from_env()

            assert registry.source_names == ["liga", "myp"]
            MockLiga.assert_called_once()
            MockMyp.assert_called_once()

    @patch.dict("os.environ", {"TCG_PROVIDER_ORDER": "myp"}, clear=False)
    @patch("src.providers.registry.log")
    def test_myp_only(self, _mock_log):
        with patch("src.providers.myp.provider.MypCardsProvider") as MockMyp:
            MockMyp.return_value = MagicMock(source_name="myp")

            registry = create_registry_from_env()

            assert registry.source_names == ["myp"]

    @patch.dict("os.environ", {"TCG_PROVIDER_ORDER": "myp,liga"}, clear=False)
    @patch("src.providers.registry.log")
    def test_reversed_order(self, _mock_log):
        with (
            patch("src.providers.liga.provider.LigaMagicProvider") as MockLiga,
            patch("src.providers.myp.provider.MypCardsProvider") as MockMyp,
        ):
            MockLiga.return_value = MagicMock(source_name="liga")
            MockMyp.return_value = MagicMock(source_name="myp")

            registry = create_registry_from_env()

            assert registry.source_names == ["myp", "liga"]

    @patch.dict("os.environ", {"TCG_PROVIDER_ORDER": "liga"}, clear=False)
    @patch("src.providers.registry.log")
    def test_liga_import_error_skipped(self, _mock_log):
        """When playwright is not installed, liga is skipped."""
        with patch(
            "builtins.__import__",
            side_effect=_import_error_for_liga,
        ):
            registry = create_registry_from_env()

            assert registry.source_names == []

    @patch.dict("os.environ", {"TCG_PROVIDER_ORDER": "liga,myp"}, clear=False)
    @patch("src.providers.registry.log")
    def test_liga_import_error_falls_back_to_myp(self, _mock_log):
        """When liga import fails, myp is still added."""
        with (
            patch(
                "builtins.__import__",
                side_effect=_import_error_for_liga,
            ),
            patch("src.providers.myp.provider.MypCardsProvider") as MockMyp,
        ):
            MockMyp.return_value = MagicMock(source_name="myp")

            registry = create_registry_from_env()

            assert registry.source_names == ["myp"]

    @patch.dict("os.environ", {"TCG_PROVIDER_ORDER": "unknown"}, clear=False)
    @patch("src.providers.registry.log")
    def test_unknown_provider_warned(self, mock_log):
        registry = create_registry_from_env()

        assert registry.source_names == []
        mock_log.warning.assert_called_with("unknown_provider", name="unknown")

    @patch.dict("os.environ", {}, clear=False)
    @patch("src.providers.registry.log")
    def test_default_env_is_liga_myp(self, _mock_log):
        """Without TCG_PROVIDER_ORDER, defaults to liga,myp."""
        # Remove the env var if it exists
        with (
            patch.dict("os.environ", {}, clear=False),
            patch("src.providers.liga.provider.LigaMagicProvider") as MockLiga,
            patch("src.providers.myp.provider.MypCardsProvider") as MockMyp,
        ):
            # Ensure env var is not set
            import os

            os.environ.pop("TCG_PROVIDER_ORDER", None)

            MockLiga.return_value = MagicMock(source_name="liga")
            MockMyp.return_value = MagicMock(source_name="myp")

            registry = create_registry_from_env()

            assert registry.source_names == ["liga", "myp"]


# Helper to simulate ImportError only for liga provider module
_real_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__


def _import_error_for_liga(name, *args, **kwargs):
    """Raise ImportError only when importing the liga provider module."""
    if "src.providers.liga" in name:
        raise ImportError("No module named 'playwright'")
    return _real_import(name, *args, **kwargs)
