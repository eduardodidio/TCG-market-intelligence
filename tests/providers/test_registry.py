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
        p1 = _make_provider("myp")
        registry = ProviderRegistry([p1])
        assert registry.source_names == ["myp"]

    def test_source_names_empty(self):
        registry = ProviderRegistry([])
        assert registry.source_names == []


class TestGetCurrentPrice:
    @pytest.mark.asyncio
    async def test_provider_succeeds(self):
        snap = _make_snapshot("myp")
        p1 = _make_provider("myp", price=snap)
        registry = ProviderRegistry([p1])

        result = await registry.get_current_price(_make_card())

        assert result is snap
        p1.get_current_price.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fallback_on_error(self):
        """First provider raises, second returns a price."""
        p1 = _make_provider("primary", price_error=RuntimeError("fail"))
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
        p1 = _make_provider("primary", price=None)
        snap = _make_snapshot("myp")
        p2 = _make_provider("myp", price=snap)
        registry = ProviderRegistry([p1, p2])

        result = await registry.get_current_price(_make_card())

        assert result is snap

    @pytest.mark.asyncio
    async def test_all_providers_fail(self):
        p1 = _make_provider("myp", price_error=RuntimeError("fail"))
        registry = ProviderRegistry([p1])

        result = await registry.get_current_price(_make_card())

        assert result is None

    @pytest.mark.asyncio
    async def test_all_providers_return_none(self):
        p1 = _make_provider("myp", price=None)
        registry = ProviderRegistry([p1])

        result = await registry.get_current_price(_make_card())

        assert result is None

    @pytest.mark.asyncio
    async def test_empty_registry(self):
        registry = ProviderRegistry([])

        result = await registry.get_current_price(_make_card())

        assert result is None


class TestGetPriceHistory:
    @pytest.mark.asyncio
    async def test_provider_returns_history(self):
        h = [HistoricalPrice(source="myp", external_id="1", observed_at=datetime.now().date())]
        p1 = _make_provider("myp", history=h)
        registry = ProviderRegistry([p1])

        result = await registry.get_price_history(_make_card())

        assert result == h

    @pytest.mark.asyncio
    async def test_fallback_on_empty_history(self):
        h = [HistoricalPrice(source="myp", external_id="1", observed_at=datetime.now().date())]
        p1 = _make_provider("primary", history=[])
        p2 = _make_provider("myp", history=h)
        registry = ProviderRegistry([p1, p2])

        result = await registry.get_price_history(_make_card())

        assert result == h

    @pytest.mark.asyncio
    async def test_all_fail_returns_empty(self):
        p1 = _make_provider("myp", history_error=RuntimeError("fail"))
        registry = ProviderRegistry([p1])

        result = await registry.get_price_history(_make_card())

        assert result == []


class TestDiscoverSets:
    @pytest.mark.asyncio
    async def test_aggregation(self):
        p1 = _make_provider("myp", sets=["SET_A", "SET_B"])
        registry = ProviderRegistry([p1])

        result = await registry.discover_sets()

        assert result == ["SET_A", "SET_B"]

    @pytest.mark.asyncio
    async def test_one_provider_errors(self):
        p1 = _make_provider("primary", sets_error=RuntimeError("fail"))
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
        p1 = _make_provider("myp", cards=cards)
        registry = ProviderRegistry([p1])

        result = await registry.discover_cards("some_set")

        assert result == cards

    @pytest.mark.asyncio
    async def test_fallback_on_empty(self):
        cards = [_make_card("2")]
        p1 = _make_provider("primary", cards=[])
        p2 = _make_provider("myp", cards=cards)
        registry = ProviderRegistry([p1, p2])

        result = await registry.discover_cards("some_set")

        assert result == cards

    @pytest.mark.asyncio
    async def test_all_empty(self):
        p1 = _make_provider("myp", cards=[])
        registry = ProviderRegistry([p1])

        result = await registry.discover_cards()

        assert result == []

    @pytest.mark.asyncio
    async def test_fallback_on_error(self):
        cards = [_make_card("2")]
        p1 = _make_provider("primary", cards_error=RuntimeError("fail"))
        p2 = _make_provider("myp", cards=cards)
        registry = ProviderRegistry([p1, p2])

        result = await registry.discover_cards()

        assert result == cards


# --- create_registry_from_env ---


class TestCreateRegistryFromEnv:
    @patch("src.providers.registry.log")
    def test_creates_myp_provider(self, _mock_log):
        with patch("src.providers.myp.provider.MypCardsProvider") as MockMyp:
            MockMyp.return_value = MagicMock(source_name="myp")

            registry = create_registry_from_env()

            assert registry.source_names == ["myp"]
            MockMyp.assert_called_once()
