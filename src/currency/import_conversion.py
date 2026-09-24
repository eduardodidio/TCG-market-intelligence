"""Import-time conversion of foreign-currency amounts to BRL (F171).

`user_collection.acquisition_price` is always stored in BRL. This module
converts amounts detected during import (e.g. USD) to BRL using a PTAX
rate looked up for the relevant date, without ever storing a foreign
amount as if it were BRL.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from src.services.currency import CurrencyConverter

RateLookup = Callable[[date], "Decimal | None"]


@dataclass
class ConversionResult:
    brl: Decimal | None
    original_amount: Decimal
    original_currency: str
    rate: Decimal | None
    warning: str | None


def to_brl(
    amount: Decimal,
    currency: str,
    on_date: date,
    rate_lookup: RateLookup,
) -> ConversionResult:
    """Convert *amount* in *currency* to BRL using a rate for *on_date*."""
    normalized_currency = currency.upper().strip()

    if normalized_currency == "BRL":
        return ConversionResult(
            brl=amount,
            original_amount=amount,
            original_currency=normalized_currency,
            rate=None,
            warning=None,
        )

    if normalized_currency != "USD":
        return ConversionResult(
            brl=None,
            original_amount=amount,
            original_currency=normalized_currency,
            rate=None,
            warning="unsupported_currency",
        )

    rate = rate_lookup(on_date)
    if rate is None or rate <= 0:
        return ConversionResult(
            brl=None,
            original_amount=amount,
            original_currency=normalized_currency,
            rate=None,
            warning="no_rate",
        )

    brl = (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return ConversionResult(
        brl=brl,
        original_amount=amount,
        original_currency=normalized_currency,
        rate=rate,
        warning=None,
    )


def rate_lookup_from_converter(converter: "CurrencyConverter") -> RateLookup:
    """Adapt a `CurrencyConverter` into a `RateLookup` callable."""
    return lambda target_date: converter.get_display_rate(target_date)
