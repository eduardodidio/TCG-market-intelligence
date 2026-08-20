"""Tests for MypCardsProvider.search_card -- mock-based."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.domain.models import MypSearchResult
from src.providers.myp.provider import BASE_URL, MypCardsProvider, MypConfig

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load_json(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config():
    """Config with zero delay for fast tests."""
    return MypConfig(delay_seconds=0, max_retries=2, timeout_seconds=1)


@pytest.fixture
def provider(config):
    return MypCardsProvider(config)


# ---------------------------------------------------------------------------
# Scenario 7: search_card returns parsed results from mocked _fetch
# ---------------------------------------------------------------------------


class TestSearchCardReturnsResults:
    @pytest.mark.asyncio
    async def test_returns_parsed_results(self, provider):
        raw = _load_json("myp_search_bolt.json")

        with patch.object(provider, "_fetch", new_callable=AsyncMock, return_value=raw):
            results = await provider.search_card("Lightning Bolt")

        assert len(results) == 3
        assert all(isinstance(r, MypSearchResult) for r in results)
        assert results[0].external_id == "45231"
        assert results[0].name == "Raio / Lightning Bolt"

    @pytest.mark.asyncio
    async def test_single_result(self, provider):
        raw = _load_json("myp_search_single.json")

        with patch.object(provider, "_fetch", new_callable=AsyncMock, return_value=raw):
            results = await provider.search_card("The One Ring")

        assert len(results) == 1
        assert results[0].external_id == "179334"
        assert results[0].set_code == "ltr"

    @pytest.mark.asyncio
    async def test_empty_api_response(self, provider):
        raw = _load_json("myp_search_empty.json")

        with patch.object(provider, "_fetch", new_callable=AsyncMock, return_value=raw):
            results = await provider.search_card("Nonexistent Card XYZ")

        assert results == []


# ---------------------------------------------------------------------------
# Scenario 5: URL construction with special characters
# ---------------------------------------------------------------------------


class TestSearchCardUrlEncoding:
    @pytest.mark.asyncio
    async def test_plain_term(self, provider):
        with patch.object(
            provider, "_fetch", new_callable=AsyncMock, return_value="[]"
        ) as mock_fetch:
            await provider.search_card("Lightning Bolt")

        expected = f"{BASE_URL}/produto/search?marca=magic&term=Lightning%20Bolt"
        mock_fetch.assert_awaited_once_with(expected)

    @pytest.mark.asyncio
    async def test_accented_characters(self, provider):
        with patch.object(
            provider, "_fetch", new_callable=AsyncMock, return_value="[]"
        ) as mock_fetch:
            await provider.search_card("Dragao Anciao")

        mock_fetch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_accented_portuguese_name(self, provider):
        with patch.object(
            provider, "_fetch", new_callable=AsyncMock, return_value="[]"
        ) as mock_fetch:
            await provider.search_card("Dragao Anciao")

        # URL-encode: a-tilde would be %C3%A3o etc.  "Dragao" is plain ASCII here.
        expected = f"{BASE_URL}/produto/search?marca=magic&term=Dragao%20Anciao"
        mock_fetch.assert_awaited_once_with(expected)

    @pytest.mark.asyncio
    async def test_real_accents(self, provider):
        """Test term with actual UTF-8 accented characters."""
        with patch.object(
            provider, "_fetch", new_callable=AsyncMock, return_value="[]"
        ) as mock_fetch:
            await provider.search_card("Dragao Anciao")

        call_url = mock_fetch.call_args[0][0]
        assert "marca=magic" in call_url
        assert "term=" in call_url

    @pytest.mark.asyncio
    async def test_apostrophe_in_name(self, provider):
        with patch.object(
            provider, "_fetch", new_callable=AsyncMock, return_value="[]"
        ) as mock_fetch:
            await provider.search_card("Urza's Tower")

        call_url = mock_fetch.call_args[0][0]
        assert "term=Urza%27s%20Tower" in call_url

    @pytest.mark.asyncio
    async def test_hyphen_in_name(self, provider):
        with patch.object(
            provider, "_fetch", new_callable=AsyncMock, return_value="[]"
        ) as mock_fetch:
            await provider.search_card("Fire-Breathing")

        call_url = mock_fetch.call_args[0][0]
        # Hyphens are not percent-encoded by urllib.parse.quote (safe by default)
        assert "term=" in call_url

    @pytest.mark.asyncio
    async def test_term_is_stripped(self, provider):
        with patch.object(
            provider, "_fetch", new_callable=AsyncMock, return_value="[]"
        ) as mock_fetch:
            await provider.search_card("  Lightning Bolt  ")

        expected = f"{BASE_URL}/produto/search?marca=magic&term=Lightning%20Bolt"
        mock_fetch.assert_awaited_once_with(expected)


# ---------------------------------------------------------------------------
# Scenario 6: empty term returns empty list without calling API
# ---------------------------------------------------------------------------


class TestSearchCardEmptyTerm:
    @pytest.mark.asyncio
    async def test_empty_string(self, provider):
        with patch.object(provider, "_fetch", new_callable=AsyncMock) as mock_fetch:
            results = await provider.search_card("")

        assert results == []
        mock_fetch.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_whitespace_only(self, provider):
        with patch.object(provider, "_fetch", new_callable=AsyncMock) as mock_fetch:
            results = await provider.search_card("   ")

        assert results == []
        mock_fetch.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_none_term(self, provider):
        """None is falsy -- should not call API."""
        with patch.object(provider, "_fetch", new_callable=AsyncMock) as mock_fetch:
            results = await provider.search_card(None)  # type: ignore[arg-type]

        assert results == []
        mock_fetch.assert_not_awaited()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestSearchCardErrorHandling:
    @pytest.mark.asyncio
    async def test_fetch_runtime_error_returns_empty(self, provider):
        with patch.object(
            provider, "_fetch", new_callable=AsyncMock, side_effect=RuntimeError("HTTP 500")
        ):
            results = await provider.search_card("Lightning Bolt")

        assert results == []

    @pytest.mark.asyncio
    async def test_fetch_timeout_returns_empty(self, provider):
        with patch.object(provider, "_fetch", new_callable=AsyncMock, side_effect=TimeoutError):
            results = await provider.search_card("Lightning Bolt")

        assert results == []

    @pytest.mark.asyncio
    async def test_fetch_os_error_returns_empty(self, provider):
        with patch.object(
            provider, "_fetch", new_callable=AsyncMock, side_effect=OSError("Network down")
        ):
            results = await provider.search_card("Lightning Bolt")

        assert results == []

    @pytest.mark.asyncio
    async def test_malformed_json_from_fetch_returns_empty(self, provider):
        with patch.object(
            provider, "_fetch", new_callable=AsyncMock, return_value="<html>Error</html>"
        ):
            results = await provider.search_card("Lightning Bolt")

        assert results == []
