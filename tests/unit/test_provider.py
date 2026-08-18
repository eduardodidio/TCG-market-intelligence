"""Mock-based unit tests for MypCardsProvider — target >= 85% coverage."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.models import (
    CardIdentity,
    HistoricalPrice,
    PriceSnapshot,
    SourceCard,
)
from src.providers.myp.provider import MypCardsProvider, MypConfig

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config():
    """Config with zero delay and small retries for fast tests."""
    return MypConfig(delay_seconds=0, max_retries=2, timeout_seconds=1)


@pytest.fixture
def provider(config):
    return MypCardsProvider(config)


def _mock_response(status_code: int = 200, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    return resp


# ---------------------------------------------------------------------------
# source_name
# ---------------------------------------------------------------------------


class TestSourceName:
    def test_returns_myp(self, provider):
        assert provider.source_name == "myp"


# ---------------------------------------------------------------------------
# _get_session / close
# ---------------------------------------------------------------------------


class TestSessionLifecycle:
    @pytest.mark.asyncio
    async def test_get_session_creates_once(self, provider):
        with patch("src.providers.myp.provider.AsyncSession", autospec=True) as MockSession:
            mock_instance = AsyncMock()
            MockSession.return_value = mock_instance

            s1 = await provider._get_session()
            s2 = await provider._get_session()
            assert s1 is s2
            MockSession.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_when_session_exists(self, provider):
        mock_session = AsyncMock()
        provider._session = mock_session

        await provider.close()

        mock_session.close.assert_awaited_once()
        assert provider._session is None

    @pytest.mark.asyncio
    async def test_close_when_no_session(self, provider):
        # Should not raise
        await provider.close()
        assert provider._session is None


# ---------------------------------------------------------------------------
# _fetch
# ---------------------------------------------------------------------------


class TestFetch:
    @pytest.mark.asyncio
    async def test_happy_path_200(self, provider):
        """200 response returns text immediately."""
        mock_session = AsyncMock()
        mock_session.get.return_value = _mock_response(200, "<html>ok</html>")
        provider._session = mock_session

        result = await provider._fetch("https://example.com")
        assert result == "<html>ok</html>"
        assert provider._request_count == 1

    @pytest.mark.asyncio
    async def test_429_retry_then_success(self, provider):
        """429 on first attempt, 200 on second."""
        mock_session = AsyncMock()
        mock_session.get.side_effect = [
            _mock_response(429),
            _mock_response(200, "ok"),
        ]
        provider._session = mock_session

        result = await provider._fetch("https://example.com")
        assert result == "ok"
        assert mock_session.get.call_count == 2
        assert provider._request_count == 2

    @pytest.mark.asyncio
    async def test_403_retry_then_success(self, provider):
        """403 on first attempt, 200 on second."""
        mock_session = AsyncMock()
        mock_session.get.side_effect = [
            _mock_response(403),
            _mock_response(200, "ok"),
        ]
        provider._session = mock_session

        result = await provider._fetch("https://example.com")
        assert result == "ok"
        assert mock_session.get.call_count == 2

    @pytest.mark.asyncio
    async def test_429_exhausted_retries(self, provider):
        """429 on all attempts raises RuntimeError (falls through loop)."""
        mock_session = AsyncMock()
        mock_session.get.side_effect = [
            _mock_response(429),
            _mock_response(429),
        ]
        provider._session = mock_session

        with pytest.raises(RuntimeError, match="Failed after 2 attempts"):
            await provider._fetch("https://example.com")

    @pytest.mark.asyncio
    async def test_403_exhausted_retries(self, provider):
        """403 on all attempts raises RuntimeError (falls through loop)."""
        mock_session = AsyncMock()
        mock_session.get.side_effect = [
            _mock_response(403),
            _mock_response(403),
        ]
        provider._session = mock_session

        with pytest.raises(RuntimeError, match="Failed after 2 attempts"):
            await provider._fetch("https://example.com")

    @pytest.mark.asyncio
    async def test_generic_4xx_raises_after_retries(self, provider):
        """500 on all attempts raises RuntimeError from the if-branch."""
        mock_session = AsyncMock()
        mock_session.get.side_effect = [
            _mock_response(500),
            _mock_response(500),
        ]
        provider._session = mock_session

        with pytest.raises(RuntimeError, match="HTTP 500"):
            await provider._fetch("https://example.com")

    @pytest.mark.asyncio
    async def test_generic_4xx_retry_then_success(self, provider):
        """500 on first attempt, 200 on second."""
        mock_session = AsyncMock()
        mock_session.get.side_effect = [
            _mock_response(500),
            _mock_response(200, "recovered"),
        ]
        provider._session = mock_session

        result = await provider._fetch("https://example.com")
        assert result == "recovered"

    @pytest.mark.asyncio
    async def test_timeout_error_raises_after_retries(self, provider):
        """TimeoutError on all attempts re-raises."""
        mock_session = AsyncMock()
        mock_session.get.side_effect = TimeoutError("connection timed out")
        provider._session = mock_session

        with pytest.raises(TimeoutError):
            await provider._fetch("https://example.com")

    @pytest.mark.asyncio
    async def test_os_error_raises_after_retries(self, provider):
        """OSError on all attempts re-raises."""
        mock_session = AsyncMock()
        mock_session.get.side_effect = OSError("network unreachable")
        provider._session = mock_session

        with pytest.raises(OSError):
            await provider._fetch("https://example.com")

    @pytest.mark.asyncio
    async def test_timeout_retry_then_success(self, provider):
        """TimeoutError on first attempt, 200 on second."""
        mock_session = AsyncMock()
        mock_session.get.side_effect = [
            TimeoutError("timeout"),
            _mock_response(200, "ok"),
        ]
        provider._session = mock_session

        result = await provider._fetch("https://example.com")
        assert result == "ok"


# ---------------------------------------------------------------------------
# discover_sets
# ---------------------------------------------------------------------------


class TestDiscoverSets:
    @pytest.mark.asyncio
    async def test_single_page(self, provider):
        """Single page of editions (no pagination links)."""
        html = """
        <html>
        <a href="/magic/dominaria-remastered">DMR</a>
        <a href="/magic/the-brothers-war">BRO</a>
        </html>
        """
        mock_session = AsyncMock()
        mock_session.get.return_value = _mock_response(200, html)
        provider._session = mock_session

        slugs = await provider.discover_sets()
        assert slugs == ["dominaria-remastered", "the-brothers-war"]

    @pytest.mark.asyncio
    async def test_multi_page(self, provider):
        """Multiple pages of editions."""
        page1 = """
        <html>
        <a href="/magic/set-a">A</a>
        <a href="?page=2">2</a>
        </html>
        """
        page2 = """
        <html>
        <a href="/magic/set-b">B</a>
        </html>
        """
        mock_session = AsyncMock()
        mock_session.get.side_effect = [
            _mock_response(200, page1),
            _mock_response(200, page2),
        ]
        provider._session = mock_session

        slugs = await provider.discover_sets()
        assert "set-a" in slugs
        assert "set-b" in slugs

    @pytest.mark.asyncio
    async def test_max_editions_pages_cap(self, provider):
        """Pagination is capped by max_editions_pages."""
        provider.config.max_editions_pages = 2
        page1 = """
        <html>
        <a href="/magic/set-a">A</a>
        <a href="?page=2">2</a>
        <a href="?page=3">3</a>
        <a href="?page=100">100</a>
        </html>
        """
        page2 = '<html><a href="/magic/set-b">B</a></html>'

        mock_session = AsyncMock()
        mock_session.get.side_effect = [
            _mock_response(200, page1),
            _mock_response(200, page2),
        ]
        provider._session = mock_session

        await provider.discover_sets()
        # Only 2 pages fetched (capped at max_editions_pages=2)
        assert mock_session.get.call_count == 2


# ---------------------------------------------------------------------------
# discover_cards / _discover_cards_in_set
# ---------------------------------------------------------------------------


class TestDiscoverCards:
    @pytest.mark.asyncio
    async def test_discover_cards_single_set(self, provider):
        """discover_cards with set_id delegates to _discover_cards_in_set."""
        html = """
        <html>
        <a href="/magic/produto/123/card-a">Card A</a>
        <a href="/magic/produto/456/card-b">Card B</a>
        </html>
        """
        mock_session = AsyncMock()
        mock_session.get.return_value = _mock_response(200, html)
        provider._session = mock_session

        cards = await provider.discover_cards(set_id="test-set")
        assert len(cards) == 2
        assert all(isinstance(c, SourceCard) for c in cards)
        ids = {c.external_id for c in cards}
        assert ids == {"123", "456"}

    @pytest.mark.asyncio
    async def test_discover_cards_all_sets(self, provider):
        """discover_cards with no set_id discovers all sets then cards."""
        editions_html = '<html><a href="/magic/set-x">X</a></html>'
        set_html = '<html><a href="/magic/produto/99/card-z">Z</a></html>'

        mock_session = AsyncMock()
        mock_session.get.side_effect = [
            _mock_response(200, editions_html),  # discover_sets page 1
            _mock_response(200, set_html),  # _discover_cards_in_set
        ]
        provider._session = mock_session

        cards = await provider.discover_cards()
        assert len(cards) == 1
        assert cards[0].external_id == "99"

    @pytest.mark.asyncio
    async def test_discover_cards_in_set_multi_page_dedup(self, provider):
        """Multi-page card discovery with duplicate removal."""
        page1 = """
        <html>
        <a href="/magic/produto/1/card-a">A</a>
        <a href="/magic/produto/2/card-b">B</a>
        <a href="?page=2">2</a>
        </html>
        """
        page2 = """
        <html>
        <a href="/magic/produto/2/card-b">B</a>
        <a href="/magic/produto/3/card-c">C</a>
        </html>
        """
        mock_session = AsyncMock()
        mock_session.get.side_effect = [
            _mock_response(200, page1),
            _mock_response(200, page2),
        ]
        provider._session = mock_session

        cards = await provider._discover_cards_in_set("test-set")
        ids = [c.external_id for c in cards]
        # card 2 appears on both pages but should only appear once
        assert len(ids) == 3
        assert sorted(ids) == ["1", "2", "3"]

    @pytest.mark.asyncio
    async def test_discover_cards_in_set_single_page(self, provider):
        """Single page, no pagination."""
        html = '<html><a href="/magic/produto/10/foo">Foo</a></html>'
        mock_session = AsyncMock()
        mock_session.get.return_value = _mock_response(200, html)
        provider._session = mock_session

        cards = await provider._discover_cards_in_set("my-set")
        assert len(cards) == 1
        assert cards[0].url == "https://mypcards.com/magic/produto/10/foo"


# ---------------------------------------------------------------------------
# get_card_details
# ---------------------------------------------------------------------------


class TestGetCardDetails:
    @pytest.mark.asyncio
    async def test_returns_parsed_card(self, provider):
        card = SourceCard(
            source="myp",
            external_id="123",
            url="https://mypcards.com/magic/produto/123/test-card",
        )
        fake_result = SourceCard(
            source="myp",
            external_id="123",
            url="https://mypcards.com/magic/produto/123/test-card",
            sku="magic_ltr_123",
            identity=CardIdentity(game="magic", name_en="Test Card"),
        )

        mock_session = AsyncMock()
        mock_session.get.return_value = _mock_response(200, "<html>card</html>")
        provider._session = mock_session

        with patch(
            "src.providers.myp.provider.parse_card_page",
            return_value=fake_result,
        ) as mock_parse:
            result = await provider.get_card_details(card)
            mock_parse.assert_called_once_with("<html>card</html>", "123", "test-card")
            assert result == fake_result

    @pytest.mark.asyncio
    async def test_returns_none_when_parser_returns_none(self, provider):
        card = SourceCard(
            source="myp",
            external_id="123",
            url="https://mypcards.com/magic/produto/123/test-card",
        )
        mock_session = AsyncMock()
        mock_session.get.return_value = _mock_response(200, "<html></html>")
        provider._session = mock_session

        with patch(
            "src.providers.myp.provider.parse_card_page",
            return_value=None,
        ):
            result = await provider.get_card_details(card)
            assert result is None


# ---------------------------------------------------------------------------
# get_current_price
# ---------------------------------------------------------------------------


class TestGetCurrentPrice:
    @pytest.mark.asyncio
    async def test_returns_parsed_snapshot(self, provider):
        card = SourceCard(
            source="myp",
            external_id="456",
            url="https://mypcards.com/magic/produto/456/price-card",
        )
        from datetime import datetime
        from decimal import Decimal

        fake_snapshot = PriceSnapshot(
            source="myp",
            external_id="456",
            observed_at=datetime.now(),
            min_price=Decimal("10.50"),
        )

        mock_session = AsyncMock()
        mock_session.get.return_value = _mock_response(200, "<html>price</html>")
        provider._session = mock_session

        with patch(
            "src.providers.myp.provider.parse_price_snapshot",
            return_value=fake_snapshot,
        ) as mock_parse:
            result = await provider.get_current_price(card)
            mock_parse.assert_called_once_with("<html>price</html>", "456")
            assert result == fake_snapshot

    @pytest.mark.asyncio
    async def test_returns_none_when_no_price(self, provider):
        card = SourceCard(
            source="myp",
            external_id="456",
            url="https://mypcards.com/magic/produto/456/price-card",
        )
        mock_session = AsyncMock()
        mock_session.get.return_value = _mock_response(200, "<html></html>")
        provider._session = mock_session

        with patch(
            "src.providers.myp.provider.parse_price_snapshot",
            return_value=None,
        ):
            result = await provider.get_current_price(card)
            assert result is None


# ---------------------------------------------------------------------------
# get_price_history
# ---------------------------------------------------------------------------


class TestGetPriceHistory:
    @pytest.mark.asyncio
    async def test_returns_parsed_history(self, provider):
        card = SourceCard(
            source="myp",
            external_id="789",
            url="https://mypcards.com/magic/produto/789/history-card",
        )
        from datetime import date
        from decimal import Decimal

        fake_history = [
            HistoricalPrice(
                source="myp",
                external_id="789",
                observed_at=date(2024, 1, 1),
                median_price=Decimal("5.00"),
            ),
        ]

        mock_session = AsyncMock()
        mock_session.get.return_value = _mock_response(200, "<html>history</html>")
        provider._session = mock_session

        with patch(
            "src.providers.myp.provider.parse_price_history",
            return_value=fake_history,
        ) as mock_parse:
            result = await provider.get_price_history(card, days=30)
            mock_parse.assert_called_once_with("<html>history</html>", "789")
            assert result == fake_history
            # Verify the URL was constructed correctly
            mock_session.get.assert_awaited_once_with(
                "https://mypcards.com/magic/preco/789/history-card?dias=30"
            )

    @pytest.mark.asyncio
    async def test_default_days_parameter(self, provider):
        card = SourceCard(
            source="myp",
            external_id="789",
            url="https://mypcards.com/magic/produto/789/history-card",
        )
        mock_session = AsyncMock()
        mock_session.get.return_value = _mock_response(200, "<html></html>")
        provider._session = mock_session

        with patch(
            "src.providers.myp.provider.parse_price_history",
            return_value=[],
        ):
            await provider.get_price_history(card)
            mock_session.get.assert_awaited_once_with(
                "https://mypcards.com/magic/preco/789/history-card?dias=1095"
            )

    @pytest.mark.asyncio
    async def test_returns_empty_list(self, provider):
        card = SourceCard(
            source="myp",
            external_id="789",
            url="https://mypcards.com/magic/produto/789/history-card",
        )
        mock_session = AsyncMock()
        mock_session.get.return_value = _mock_response(200, "<html></html>")
        provider._session = mock_session

        with patch(
            "src.providers.myp.provider.parse_price_history",
            return_value=[],
        ):
            result = await provider.get_price_history(card)
            assert result == []


# ---------------------------------------------------------------------------
# Config defaults
# ---------------------------------------------------------------------------


class TestMypConfig:
    def test_default_config(self):
        config = MypConfig()
        assert config.delay_seconds == 1.0
        assert config.max_retries == 3
        assert config.timeout_seconds == 30.0
        assert config.history_days == 1095
        assert config.max_editions_pages == 50

    def test_provider_uses_default_config(self):
        p = MypCardsProvider()
        assert p.config.delay_seconds == 1.0

    def test_provider_accepts_custom_config(self):
        cfg = MypConfig(delay_seconds=0, max_retries=1)
        p = MypCardsProvider(cfg)
        assert p.config.delay_seconds == 0
        assert p.config.max_retries == 1
