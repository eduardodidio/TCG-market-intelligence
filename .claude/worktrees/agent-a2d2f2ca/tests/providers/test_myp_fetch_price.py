"""Tests for MypCardsProvider.fetch_current_price -- mock-based."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from src.domain.models import JsonLdPrice
from src.providers.myp.provider import BASE_URL, MypCardsProvider, MypConfig

# ---------------------------------------------------------------------------
# Sample HTML with valid JSON-LD Product block
# ---------------------------------------------------------------------------

VALID_JSONLD_HTML = """
<html>
<head>
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "Tutor Esclarecido",
    "sku": "magic_dmr_001",
    "offers": {
        "@type": "Offer",
        "price": "25.50",
        "priceCurrency": "BRL",
        "availability": "https://schema.org/InStock"
    }
}
</script>
</head>
<body><h1>Tutor Esclarecido</h1></body>
</html>
"""

NO_JSONLD_HTML = """
<html>
<head><title>MYP Cards</title></head>
<body><h1>Some Page</h1></body>
</html>
"""

ZERO_PRICE_HTML = """
<html>
<head>
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "Carta Esgotada",
    "sku": "magic_dmr_999",
    "offers": {
        "@type": "Offer",
        "price": "0",
        "priceCurrency": "BRL",
        "availability": "https://schema.org/OutOfStock"
    }
}
</script>
</head>
<body></body>
</html>
"""


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
# Happy path: valid JSON-LD returns JsonLdPrice
# ---------------------------------------------------------------------------


class TestFetchCurrentPriceHappyPath:
    @pytest.mark.asyncio
    async def test_returns_jsonld_price(self, provider):
        with patch.object(
            provider, "_fetch", new_callable=AsyncMock, return_value=VALID_JSONLD_HTML
        ):
            result = await provider.fetch_current_price("179334", "tutor-esclarecido")

        assert result is not None
        assert isinstance(result, JsonLdPrice)
        assert result.price == Decimal("25.50")
        assert result.currency == "BRL"
        assert result.availability == "InStock"

    @pytest.mark.asyncio
    async def test_zero_price_returns_none_price(self, provider):
        """Price of 0 is treated as None (no meaningful price data)."""
        with patch.object(provider, "_fetch", new_callable=AsyncMock, return_value=ZERO_PRICE_HTML):
            result = await provider.fetch_current_price("179334", "carta-esgotada")

        assert result is not None
        assert isinstance(result, JsonLdPrice)
        assert result.price is None
        assert result.availability == "OutOfStock"


# ---------------------------------------------------------------------------
# URL construction
# ---------------------------------------------------------------------------


class TestFetchCurrentPriceUrl:
    @pytest.mark.asyncio
    async def test_url_construction(self, provider):
        with patch.object(
            provider, "_fetch", new_callable=AsyncMock, return_value=VALID_JSONLD_HTML
        ) as mock_fetch:
            await provider.fetch_current_price("179334", "tutor-esclarecido")

        expected_url = f"{BASE_URL}/magic/produto/179334/tutor-esclarecido"
        mock_fetch.assert_awaited_once_with(expected_url)

    @pytest.mark.asyncio
    async def test_url_with_different_ids(self, provider):
        with patch.object(
            provider, "_fetch", new_callable=AsyncMock, return_value=VALID_JSONLD_HTML
        ) as mock_fetch:
            await provider.fetch_current_price("45231", "raio-lightning-bolt")

        expected_url = f"{BASE_URL}/magic/produto/45231/raio-lightning-bolt"
        mock_fetch.assert_awaited_once_with(expected_url)


# ---------------------------------------------------------------------------
# Error handling: fetch failures return None
# ---------------------------------------------------------------------------


class TestFetchCurrentPriceErrors:
    @pytest.mark.asyncio
    async def test_runtime_error_returns_none(self, provider):
        with patch.object(
            provider,
            "_fetch",
            new_callable=AsyncMock,
            side_effect=RuntimeError("HTTP 500"),
        ):
            result = await provider.fetch_current_price("179334", "tutor-esclarecido")

        assert result is None

    @pytest.mark.asyncio
    async def test_timeout_error_returns_none(self, provider):
        with patch.object(provider, "_fetch", new_callable=AsyncMock, side_effect=TimeoutError):
            result = await provider.fetch_current_price("179334", "tutor-esclarecido")

        assert result is None

    @pytest.mark.asyncio
    async def test_os_error_returns_none(self, provider):
        with patch.object(
            provider,
            "_fetch",
            new_callable=AsyncMock,
            side_effect=OSError("Network down"),
        ):
            result = await provider.fetch_current_price("179334", "tutor-esclarecido")

        assert result is None


# ---------------------------------------------------------------------------
# No JSON-LD: parse returns None
# ---------------------------------------------------------------------------


class TestFetchCurrentPriceNoJsonLd:
    @pytest.mark.asyncio
    async def test_html_without_jsonld_returns_none(self, provider):
        """HTML without Product JSON-LD returns None from parser."""
        with patch.object(provider, "_fetch", new_callable=AsyncMock, return_value=NO_JSONLD_HTML):
            result = await provider.fetch_current_price("179334", "tutor-esclarecido")

        assert result is None

    @pytest.mark.asyncio
    async def test_parse_returns_none_passthrough(self, provider):
        """When parse_jsonld_price returns None, fetch_current_price returns None."""
        with (
            patch.object(
                provider, "_fetch", new_callable=AsyncMock, return_value=NO_JSONLD_HTML
            ) as mock_fetch,
            patch("src.providers.myp.provider.parse_jsonld_price", return_value=None),
        ):
            result = await provider.fetch_current_price("179334", "some-slug")

        assert result is None
        mock_fetch.assert_awaited_once()
