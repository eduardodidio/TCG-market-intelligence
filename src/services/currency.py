"""Currency conversion service using stored exchange rates."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.database.repository import Repository


class CurrencyConverter:
    """Convert BRL prices to USD using stored PTAX exchange rates.

    Uses an in-memory cache to avoid repeated DB lookups for the same date.
    Conversion is read-time only -- BRL remains the storage currency.
    """

    def __init__(self, repo: Repository):
        self._repo = repo
        self._cache: dict[date, Decimal] = {}

    def convert(
        self,
        value: Decimal | float | None,
        from_date: date,
        to_currency: str,
    ) -> Decimal | None:
        """Convert a BRL value to the target currency.

        Returns the original value unchanged if to_currency is BRL.
        Returns None if the value is None or no exchange rate is available.
        """
        if to_currency in ("BRL", "PILA") or value is None:
            return Decimal(str(value)) if value is not None else None

        rate = self._get_rate(from_date)
        if rate is None:
            return None

        decimal_value = Decimal(str(value)) if not isinstance(value, Decimal) else value
        return (decimal_value / rate).quantize(Decimal("0.01"))

    def get_display_rate(self, target_date: date | None = None) -> Decimal | None:
        """Get the exchange rate for display purposes."""
        if target_date is None:
            target_date = date.today()
        return self._get_rate(target_date)

    def _get_rate(self, target_date: date) -> Decimal | None:
        """Get the exchange rate for a date, with caching."""
        if target_date in self._cache:
            return self._cache[target_date]

        row = self._repo.get_closest_rate(target_date)
        if row is None:
            return None

        self._cache[target_date] = row.rate
        return row.rate
