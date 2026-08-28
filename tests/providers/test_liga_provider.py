"""Tests for LigaMagic provider -- mock-based, no real browser needed."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.domain.models import CardIdentity, PriceSnapshot, SourceCard
from src.providers.liga.config import LigaConfig
from src.providers.liga.exceptions import (
    LigaError,
    LigaNotFoundError,
    LigaRateLimitError,
    LigaServerError,
)
from src.providers.liga.provider import (
    BASE_URL,
    LigaMagicProvider,
    _build_card_url,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load_html(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    def test_liga_error_is_runtime_error(self):
        assert issubclass(LigaError, RuntimeError)

    def test_not_found_is_liga_error(self):
        assert issubclass(LigaNotFoundError, LigaError)

    def test_rate_limit_is_liga_error(self):
        assert issubclass(LigaRateLimitError, LigaError)

    def test_server_error_is_liga_error(self):
        assert issubclass(LigaServerError, LigaError)

    def test_liga_error_fields(self):
        err = LigaError("test", url="http://x", status_code=500, attempts=3)
        assert str(err) == "test"
        assert err.url == "http://x"
        assert err.status_code == 500
        assert err.attempts == 3

    def test_liga_error_defaults(self):
        err = LigaError("msg")
        assert err.url == ""
        assert err.status_code == 0
        assert err.attempts == 1


# ---------------------------------------------------------------------------
# Config defaults
# ---------------------------------------------------------------------------


class TestLigaConfig:
    def test_defaults(self):
        config = LigaConfig()
        assert config.delay_seconds == 4.0
        assert config.timeout_seconds == 30.0
        assert config.headless is True
        assert config.max_retries == 2

    def test_custom_values(self):
        config = LigaConfig(delay_seconds=2.0, headless=False, max_retries=5)
        assert config.delay_seconds == 2.0
        assert config.headless is False
        assert config.max_retries == 5


# ---------------------------------------------------------------------------
# URL construction
# ---------------------------------------------------------------------------


class TestBuildCardUrl:
    def test_simple_name(self):
        url = _build_card_url("Lightning Bolt")
        assert url == f"{BASE_URL}/?view=cards/card&card=Lightning+Bolt&show=1"

    def test_name_with_apostrophe(self):
        url = _build_card_url("Urza's Tower")
        assert "card=Urza" in url
        assert "show=1" in url

    def test_name_stripped(self):
        url = _build_card_url("  Sol Ring  ")
        assert "card=Sol+Ring" in url

    def test_name_with_comma(self):
        url = _build_card_url("Kolaghan, the Storm's Fury")
        assert "card=Kolaghan" in url


# ---------------------------------------------------------------------------
# Provider source_name
# ---------------------------------------------------------------------------


class TestProviderSourceName:
    def test_source_name(self):
        provider = LigaMagicProvider()
        assert provider.source_name == "liga"


# ---------------------------------------------------------------------------
# Stub methods return empty
# ---------------------------------------------------------------------------


class TestStubMethods:
    @pytest.fixture
    def provider(self):
        return LigaMagicProvider(LigaConfig(delay_seconds=0, max_retries=1))

    @pytest.mark.asyncio
    async def test_discover_sets_empty(self, provider):
        result = await provider.discover_sets()
        assert result == []

    @pytest.mark.asyncio
    async def test_discover_cards_empty(self, provider):
        result = await provider.discover_cards()
        assert result == []

    @pytest.mark.asyncio
    async def test_discover_cards_with_set_empty(self, provider):
        result = await provider.discover_cards(set_id="alpha")
        assert result == []

    @pytest.mark.asyncio
    async def test_price_history_empty(self, provider):
        card = SourceCard(source="liga", external_id="1", url="http://x")
        result = await provider.get_price_history(card)
        assert result == []

    @pytest.mark.asyncio
    async def test_price_history_with_days(self, provider):
        card = SourceCard(source="liga", external_id="1", url="http://x")
        result = await provider.get_price_history(card, days=30)
        assert result == []


# ---------------------------------------------------------------------------
# get_current_price with mocked _fetch_page
# ---------------------------------------------------------------------------


class TestGetCurrentPrice:
    @pytest.fixture
    def provider(self):
        return LigaMagicProvider(LigaConfig(delay_seconds=0, max_retries=1))

    @pytest.mark.asyncio
    async def test_returns_snapshot_with_prices(self, provider):
        html = _load_html("liga_card_bolt.html")
        with patch.object(provider, "_fetch_page", new_callable=AsyncMock, return_value=html):
            card = SourceCard(
                source="liga",
                external_id="12345",
                url="http://ligamagic/card",
                identity=CardIdentity(game="magic", name_en="Lightning Bolt"),
            )
            result = await provider.get_current_price(card)

        assert result is not None
        assert isinstance(result, PriceSnapshot)
        assert result.source == "liga"
        assert result.external_id == "12345"
        assert result.currency == "BRL"
        assert result.min_price is not None
        assert result.avg_price is not None

    @pytest.mark.asyncio
    async def test_returns_none_for_no_prices(self, provider):
        html = _load_html("liga_card_no_prices.html")
        with patch.object(provider, "_fetch_page", new_callable=AsyncMock, return_value=html):
            card = SourceCard(
                source="liga",
                external_id="99999",
                url="http://ligamagic/card",
                identity=CardIdentity(game="magic", name_en="Nonexistent"),
            )
            result = await provider.get_current_price(card)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_not_found_error(self, provider):
        with patch.object(
            provider,
            "_fetch_page",
            new_callable=AsyncMock,
            side_effect=LigaNotFoundError("404", url="x", status_code=404),
        ):
            card = SourceCard(
                source="liga",
                external_id="bad",
                url="http://ligamagic/bad",
            )
            result = await provider.get_current_price(card)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_liga_error(self, provider):
        with patch.object(
            provider,
            "_fetch_page",
            new_callable=AsyncMock,
            side_effect=LigaError("Server broke", url="x", status_code=500),
        ):
            card = SourceCard(
                source="liga",
                external_id="err",
                url="http://ligamagic/err",
            )
            result = await provider.get_current_price(card)

        assert result is None

    @pytest.mark.asyncio
    async def test_uses_card_url_when_available(self, provider):
        html = _load_html("liga_card_single_price.html")
        with patch.object(
            provider, "_fetch_page", new_callable=AsyncMock, return_value=html
        ) as mock_fetch:
            card = SourceCard(
                source="liga",
                external_id="42",
                url="http://ligamagic/custom-url",
            )
            await provider.get_current_price(card)

        mock_fetch.assert_awaited_once_with("http://ligamagic/custom-url")

    @pytest.mark.asyncio
    async def test_builds_url_from_name_when_no_url(self, provider):
        html = _load_html("liga_card_single_price.html")
        with patch.object(
            provider, "_fetch_page", new_callable=AsyncMock, return_value=html
        ) as mock_fetch:
            card = SourceCard(
                source="liga",
                external_id="42",
                url="",
                identity=CardIdentity(game="magic", name_en="Sol Ring"),
            )
            await provider.get_current_price(card)

        expected_url = f"{BASE_URL}/?view=cards/card&card=Sol+Ring&show=1"
        mock_fetch.assert_awaited_once_with(expected_url)


# ---------------------------------------------------------------------------
# search_card convenience method
# ---------------------------------------------------------------------------


class TestSearchCard:
    @pytest.fixture
    def provider(self):
        return LigaMagicProvider(LigaConfig(delay_seconds=0, max_retries=1))

    @pytest.mark.asyncio
    async def test_empty_name_returns_empty_prices(self, provider):
        result = await provider.search_card("")
        assert result["normal"]["low"] is None

    @pytest.mark.asyncio
    async def test_whitespace_name_returns_empty(self, provider):
        result = await provider.search_card("   ")
        assert result["normal"]["low"] is None

    @pytest.mark.asyncio
    async def test_returns_parsed_prices(self, provider):
        html = _load_html("liga_card_bolt.html")
        with patch.object(provider, "_fetch_page", new_callable=AsyncMock, return_value=html):
            result = await provider.search_card("Lightning Bolt")

        assert result["card_name"] == "Lightning Bolt"
        assert result["normal"]["low"] is not None

    @pytest.mark.asyncio
    async def test_liga_error_is_reraised(self, provider):
        """LigaError from _fetch_page is re-raised (not swallowed)."""
        with patch.object(
            provider,
            "_fetch_page",
            new_callable=AsyncMock,
            side_effect=LigaError("fail"),
        ):
            with pytest.raises(LigaError, match="fail"):
                await provider.search_card("Lightning Bolt")

    @pytest.mark.asyncio
    async def test_unexpected_error_wraps_to_liga_error(self, provider):
        """Non-LigaError exceptions are wrapped into LigaError with type name."""
        with patch.object(
            provider,
            "_fetch_page",
            new_callable=AsyncMock,
            side_effect=RuntimeError("something broke"),
        ):
            with pytest.raises(LigaError, match="Unexpected RuntimeError: something broke"):
                await provider.search_card("Lightning Bolt")

    @pytest.mark.asyncio
    async def test_empty_message_exception_wraps_with_type(self, provider):
        """Exception with empty str() gets type name in wrapped LigaError."""
        with patch.object(
            provider,
            "_fetch_page",
            new_callable=AsyncMock,
            side_effect=RuntimeError(""),
        ):
            with pytest.raises(LigaError, match="Unexpected RuntimeError \\(no message\\)"):
                await provider.search_card("Lightning Bolt")

    @pytest.mark.asyncio
    async def test_unexpected_error_preserves_cause(self, provider):
        """Wrapped LigaError should chain the original exception."""
        original = ValueError("root cause")
        with patch.object(
            provider,
            "_fetch_page",
            new_callable=AsyncMock,
            side_effect=original,
        ):
            with pytest.raises(LigaError) as exc_info:
                await provider.search_card("Lightning Bolt")
            assert exc_info.value.__cause__ is original


# ---------------------------------------------------------------------------
# _fetch_page error message improvement
# ---------------------------------------------------------------------------


class TestFetchPageErrorMessages:
    """_fetch_page produces descriptive error messages including exception type."""

    @pytest.fixture
    def provider(self):
        return LigaMagicProvider(LigaConfig(delay_seconds=0, max_retries=1))

    @pytest.mark.asyncio
    async def test_timeout_error_includes_type_in_message(self, provider):
        with patch.object(
            provider,
            "_ensure_page",
            new_callable=AsyncMock,
        ) as mock_ensure:
            mock_page = AsyncMock()
            mock_page.goto = AsyncMock(side_effect=TimeoutError("page.goto timed out"))
            mock_ensure.return_value = mock_page

            with pytest.raises(LigaError, match=r"TimeoutError.*page\.goto timed out"):
                await provider._fetch_page("http://example.com")

    @pytest.mark.asyncio
    async def test_empty_message_error_includes_type(self, provider):
        with patch.object(
            provider,
            "_ensure_page",
            new_callable=AsyncMock,
        ) as mock_ensure:
            mock_page = AsyncMock()
            mock_page.goto = AsyncMock(side_effect=OSError(""))
            mock_ensure.return_value = mock_page

            with pytest.raises(LigaError, match=r"OSError, no details"):
                await provider._fetch_page("http://example.com")

    @pytest.mark.asyncio
    async def test_os_error_includes_type_in_message(self, provider):
        with patch.object(
            provider,
            "_ensure_page",
            new_callable=AsyncMock,
        ) as mock_ensure:
            mock_page = AsyncMock()
            mock_page.goto = AsyncMock(side_effect=OSError("Connection refused"))
            mock_ensure.return_value = mock_page

            with pytest.raises(LigaError, match=r"OSError.*Connection refused"):
                await provider._fetch_page("http://example.com")


# ---------------------------------------------------------------------------
# Lifecycle (open/close)
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_initial_state(self):
        provider = LigaMagicProvider()
        assert provider._page is None
        assert provider._browser is None
        assert provider._playwright is None
        assert provider._request_count == 0

    @pytest.mark.asyncio
    async def test_close_when_not_opened(self):
        """close() should not raise when browser was never opened."""
        provider = LigaMagicProvider()
        await provider.close()  # Should not raise
        assert provider._page is None
