"""Tests for BCB PTAX API client (T02)."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from src.providers.bcb.client import fetch_daily_rate, fetch_rate_range


def _make_mock_client(response_json, *, raise_error=None):
    """Build a patched httpx.AsyncClient context manager."""
    mock_response = MagicMock()
    mock_response.json.return_value = response_json
    mock_response.raise_for_status = MagicMock()

    mock_instance = AsyncMock()
    if raise_error:
        mock_instance.get.side_effect = raise_error
    else:
        mock_instance.get.return_value = mock_response

    return mock_instance


class TestFetchDailyRate:
    async def test_returns_exchange_rate(self):
        response_data = {
            "value": [
                {
                    "cotacaoCompra": 5.1234,
                    "cotacaoVenda": 5.2500,
                    "dataHoraCotacao": "2026-08-20 13:11:10.123",
                }
            ]
        }
        mock_client = _make_mock_client(response_data)

        with patch("src.providers.bcb.client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await fetch_daily_rate(date(2026, 8, 20))

        assert result is not None
        assert result.rate_date == date(2026, 8, 20)
        assert result.rate == Decimal("5.25")
        assert result.from_currency == "USD"
        assert result.to_currency == "BRL"
        assert result.source == "bcb_ptax"

    async def test_returns_none_for_empty_values(self):
        mock_client = _make_mock_client({"value": []})

        with patch("src.providers.bcb.client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await fetch_daily_rate(date(2026, 8, 17))

        assert result is None

    async def test_returns_none_on_http_error(self):
        error = httpx.HTTPStatusError(
            "500",
            request=httpx.Request("GET", "http://test"),
            response=httpx.Response(500),
        )
        mock_client = _make_mock_client({}, raise_error=error)

        with patch("src.providers.bcb.client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await fetch_daily_rate(date(2026, 8, 20))

        assert result is None

    async def test_uses_today_when_no_date(self):
        response_data = {
            "value": [
                {
                    "cotacaoCompra": 5.10,
                    "cotacaoVenda": 5.20,
                    "dataHoraCotacao": "2026-08-21 13:00:00.000",
                }
            ]
        }
        mock_client = _make_mock_client(response_data)

        with patch("src.providers.bcb.client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await fetch_daily_rate()

        assert result is not None
        assert result.rate_date == date.today()

    async def test_returns_none_when_cotacao_missing(self):
        response_data = {"value": [{"cotacaoCompra": 5.0}]}
        mock_client = _make_mock_client(response_data)

        with patch("src.providers.bcb.client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await fetch_daily_rate(date(2026, 8, 20))

        assert result is None


class TestFetchRateRange:
    async def test_returns_list_of_rates(self):
        response_data = {
            "value": [
                {
                    "cotacaoCompra": 5.10,
                    "cotacaoVenda": 5.20,
                    "dataHoraCotacao": "2026-08-18 13:11:10.123",
                },
                {
                    "cotacaoCompra": 5.15,
                    "cotacaoVenda": 5.25,
                    "dataHoraCotacao": "2026-08-19 13:11:10.123",
                },
                {
                    "cotacaoCompra": 5.20,
                    "cotacaoVenda": 5.30,
                    "dataHoraCotacao": "2026-08-20 13:11:10.123",
                },
            ]
        }
        mock_client = _make_mock_client(response_data)

        with patch("src.providers.bcb.client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            results = await fetch_rate_range(date(2026, 8, 18), date(2026, 8, 20))

        assert len(results) == 3
        assert results[0].rate_date == date(2026, 8, 18)
        assert results[0].rate == Decimal("5.2")
        assert results[2].rate_date == date(2026, 8, 20)
        assert results[2].rate == Decimal("5.3")

    async def test_returns_empty_list_on_error(self):
        error = httpx.HTTPStatusError(
            "500",
            request=httpx.Request("GET", "http://test"),
            response=httpx.Response(500),
        )
        mock_client = _make_mock_client({}, raise_error=error)

        with patch("src.providers.bcb.client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            results = await fetch_rate_range(date(2026, 8, 18), date(2026, 8, 20))

        assert results == []

    async def test_skips_entries_without_cotacao(self):
        response_data = {
            "value": [
                {
                    "cotacaoVenda": 5.20,
                    "dataHoraCotacao": "2026-08-18 13:11:10.123",
                },
                {
                    "cotacaoCompra": 5.15,
                    "dataHoraCotacao": "2026-08-19 13:11:10.123",
                },
            ]
        }
        mock_client = _make_mock_client(response_data)

        with patch("src.providers.bcb.client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            results = await fetch_rate_range(date(2026, 8, 18), date(2026, 8, 19))

        assert len(results) == 1
        assert results[0].rate_date == date(2026, 8, 18)
