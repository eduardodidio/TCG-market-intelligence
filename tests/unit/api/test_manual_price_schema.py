"""Unit tests for ManualPriceRequest schema validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.api.schemas.collection import ManualPriceRequest


class TestManualPriceRequest:
    def test_valid_brl_price(self) -> None:
        req = ManualPriceRequest(price=10.50)
        assert req.price == 10.50
        assert req.currency == "BRL"

    def test_valid_usd_price(self) -> None:
        req = ManualPriceRequest(price=5.0, currency="USD")
        assert req.price == 5.0
        assert req.currency == "USD"

    def test_valid_pila_price(self) -> None:
        req = ManualPriceRequest(price=100.0, currency="PILA")
        assert req.currency == "PILA"

    def test_rejects_negative_price(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ManualPriceRequest(price=-1.0)
        assert "positive" in str(exc_info.value).lower()

    def test_rejects_zero_price(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ManualPriceRequest(price=0.0)
        assert "positive" in str(exc_info.value).lower()

    def test_rejects_price_over_max(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ManualPriceRequest(price=100000.0)
        assert "99999.99" in str(exc_info.value)

    def test_accepts_max_price(self) -> None:
        req = ManualPriceRequest(price=99999.99)
        assert req.price == 99999.99

    def test_rejects_invalid_currency(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ManualPriceRequest(price=10.0, currency="EUR")
        assert "currency" in str(exc_info.value).lower()

    def test_default_currency_is_brl(self) -> None:
        req = ManualPriceRequest(price=1.0)
        assert req.currency == "BRL"
