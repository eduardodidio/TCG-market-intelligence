"""Pure analytics indicator functions for TCG price data.

All functions are pure — no database imports, no side effects.
All price arithmetic uses Decimal exclusively.
"""

from __future__ import annotations

import decimal
from datetime import date, datetime, timedelta
from decimal import Decimal

from src.domain.models import (
    CardAnalytics,
    HistoricalPrice,
    Momentum,
    MovingAverage,
    PriceExtremes,
    Volatility,
)


def _extract_valid_prices(
    prices: list[HistoricalPrice], price_field: str
) -> list[tuple[date, Decimal]]:
    """Extract (date, price) tuples where price is not None."""
    result: list[tuple[date, Decimal]] = []
    for p in prices:
        val = getattr(p, price_field, None)
        if val is not None:
            result.append((p.observed_at, val))
    return result


def compute_moving_average(
    prices: list[HistoricalPrice],
    period: int,
    price_field: str = "median_price",
) -> MovingAverage | None:
    """Simple moving average of the last ``period`` observations.

    Returns None if fewer than ``period`` non-None values exist.
    """
    valid = _extract_valid_prices(prices, price_field)
    if len(valid) < period:
        return None

    # Use the last `period` values (by list order, assumed chronological)
    last_n = valid[-period:]
    total = sum(v for _, v in last_n)
    avg = total / period

    return MovingAverage(
        period=period,
        value=avg,
        price_field=price_field,
        calculated_at=last_n[-1][0],
    )


def compute_all_moving_averages(
    prices: list[HistoricalPrice],
    periods: list[int] | None = None,
    price_field: str = "median_price",
) -> list[MovingAverage]:
    """Compute moving averages for standard periods, skipping insufficient data."""
    if periods is None:
        periods = [7, 30, 90]

    results: list[MovingAverage] = []
    for period in periods:
        ma = compute_moving_average(prices, period, price_field)
        if ma is not None:
            results.append(ma)
    return results


def compute_price_extremes(
    prices: list[HistoricalPrice],
    price_field: str = "median_price",
) -> PriceExtremes | None:
    """Find all-time high and all-time low with their dates.

    Returns None if no valid price data.
    """
    valid = _extract_valid_prices(prices, price_field)
    if not valid:
        return None

    ath_date, ath_price = max(valid, key=lambda x: x[1])
    atl_date, atl_price = min(valid, key=lambda x: x[1])

    return PriceExtremes(
        ath_price=ath_price,
        ath_date=ath_date,
        atl_price=atl_price,
        atl_date=atl_date,
        price_field=price_field,
    )


def compute_volatility(
    prices: list[HistoricalPrice],
    period_days: int | None = None,
    price_field: str = "median_price",
) -> Volatility | None:
    """Compute population standard deviation and coefficient of variation.

    Uses **population** std dev (divides by N, not N-1) since we have the
    full set of observed prices, not a sample.

    If ``period_days`` is set, uses only the last N days of data.
    Returns None if fewer than 2 valid prices.
    """
    valid = _extract_valid_prices(prices, price_field)

    if period_days is not None and valid:
        # Filter to last N days based on the most recent date
        latest_date = max(d for d, _ in valid)
        cutoff = latest_date - timedelta(days=period_days)
        valid = [(d, v) for d, v in valid if d >= cutoff]

    if len(valid) < 2:
        return None

    values = [v for _, v in valid]
    n = len(values)
    mean = sum(values) / n

    # Population variance
    variance = sum((v - mean) ** 2 for v in values) / n

    # Decimal sqrt with proper context
    ctx = decimal.getcontext()
    std_dev = variance.sqrt(ctx)

    # Coefficient of variation
    if mean == 0:
        coeff_var = Decimal("0")
    else:
        coeff_var = std_dev / mean

    actual_period = period_days if period_days is not None else n

    return Volatility(
        period_days=actual_period,
        std_dev=std_dev,
        coefficient_of_variation=coeff_var,
        price_field=price_field,
    )


def compute_momentum(
    prices: list[HistoricalPrice],
    period_days: int = 7,
    price_field: str = "median_price",
) -> Momentum | None:
    """Compute rate of change and trend direction.

    Rate of change = (current - past) / past * 100 as percentage.
    Trend: "up" if RoC > 1, "down" if RoC < -1, "flat" otherwise.
    Returns None if insufficient data.
    """
    valid = _extract_valid_prices(prices, price_field)
    if len(valid) < 2:
        return None

    # Current = last valid price
    current_date, current_price = valid[-1]

    # Past = price nearest to `period_days` ago
    target_date = current_date - timedelta(days=period_days)

    # Find the observation closest to target_date
    past_date, past_price = min(
        valid[:-1],  # exclude current
        key=lambda x: abs((x[0] - target_date).days),
    )

    if past_price == 0:
        return None

    roc = (current_price - past_price) / past_price * Decimal("100")

    if roc > Decimal("1"):
        trend = "up"
    elif roc < Decimal("-1"):
        trend = "down"
    else:
        trend = "flat"

    return Momentum(
        period_days=period_days,
        rate_of_change=roc,
        trend_direction=trend,
        price_field=price_field,
    )


def compute_card_analytics(
    prices: list[HistoricalPrice],
    source: str,
    external_id: str,
    price_field: str = "median_price",
) -> CardAnalytics:
    """Orchestrator: compute all indicators and assemble CardAnalytics."""
    moving_averages = compute_all_moving_averages(
        prices, periods=[7, 30, 90], price_field=price_field
    )
    extremes = compute_price_extremes(prices, price_field=price_field)
    volatility = compute_volatility(
        prices, period_days=30, price_field=price_field
    )
    momentum = compute_momentum(
        prices, period_days=7, price_field=price_field
    )

    return CardAnalytics(
        external_id=external_id,
        source=source,
        moving_averages=moving_averages,
        extremes=extremes,
        volatility=volatility,
        momentum=momentum,
        computed_at=datetime.now(),
    )
