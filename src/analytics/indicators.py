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
    PerformanceScore,
    PeriodComparison,
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


def compute_performance_score(
    prices: list[HistoricalPrice],
    period_days: int = 30,
    price_field: str = "median_price",
) -> PerformanceScore | None:
    """Compute a composite performance score (0-100) for a price series.

    Sub-scores:
      - Momentum (40%): maps rate_of_change from [-50, +50] to [0, 100]
      - Trend consistency (30%): fraction of positive daily deltas
      - ATH proximity (30%): current_price / ath_price * 100

    Returns None if fewer than 3 valid data points in the period.
    """
    valid = _extract_valid_prices(prices, price_field)

    if valid:
        latest_date = max(d for d, _ in valid)
        cutoff = latest_date - timedelta(days=period_days)
        period_valid = [(d, v) for d, v in valid if d >= cutoff]
    else:
        period_valid = []

    if len(period_valid) < 3:
        return None

    # Sort chronologically
    period_valid.sort(key=lambda x: x[0])

    # --- Momentum sub-score ---
    first_price = period_valid[0][1]
    last_price = period_valid[-1][1]
    if first_price == 0:
        roc = Decimal("0")
    else:
        roc = (last_price - first_price) / first_price * Decimal("100")
    # Map [-50, +50] to [0, 100], clamped
    raw = (roc + Decimal("50")) * Decimal("100") / Decimal("100")
    momentum_score = int(min(Decimal("100"), max(Decimal("0"), raw)))

    # --- Trend consistency sub-score ---
    deltas = []
    for i in range(1, len(period_valid)):
        delta = period_valid[i][1] - period_valid[i - 1][1]
        deltas.append(delta)
    if deltas:
        positive_count = sum(1 for d in deltas if d > 0)
        ratio = Decimal(str(positive_count)) / Decimal(str(len(deltas)))
        consistency_score = int(ratio * Decimal("100"))
    else:
        consistency_score = 50

    # --- ATH proximity sub-score (over full dataset, not just period) ---
    all_valid = _extract_valid_prices(prices, price_field)
    if all_valid:
        ath_price = max(v for _, v in all_valid)
        if ath_price > 0:
            ath_proximity = int(last_price / ath_price * Decimal("100"))
        else:
            ath_proximity = 0
    else:
        ath_proximity = 0

    # Clamp sub-scores
    momentum_score = max(0, min(100, momentum_score))
    consistency_score = max(0, min(100, consistency_score))
    ath_proximity = max(0, min(100, ath_proximity))

    # Weighted average: momentum 40%, consistency 30%, ATH proximity 30%
    score = int(
        Decimal(str(momentum_score)) * Decimal("0.4")
        + Decimal(str(consistency_score)) * Decimal("0.3")
        + Decimal(str(ath_proximity)) * Decimal("0.3")
    )
    score = max(0, min(100, score))

    if score >= 70:
        label = "strong"
    elif score >= 45:
        label = "moderate"
    elif score >= 25:
        label = "weak"
    else:
        label = "declining"

    return PerformanceScore(
        score=score,
        label=label,
        period_days=period_days,
        price_field=price_field,
    )


def compute_period_comparison(
    prices: list[HistoricalPrice],
    period_days: int = 30,
    price_field: str = "median_price",
) -> PeriodComparison | None:
    """Compare current period average price vs previous period of equal length.

    Returns None if either period has fewer than 1 data point.
    """
    valid = _extract_valid_prices(prices, price_field)
    if not valid:
        return None

    valid.sort(key=lambda x: x[0])
    latest_date = max(d for d, _ in valid)

    # Current period: last period_days days
    current_cutoff = latest_date - timedelta(days=period_days)
    current_data = [(d, v) for d, v in valid if d >= current_cutoff]

    # Previous period: period_days days before current_cutoff
    previous_cutoff = current_cutoff - timedelta(days=period_days)
    previous_data = [(d, v) for d, v in valid if previous_cutoff <= d < current_cutoff]

    if len(current_data) < 1 or len(previous_data) < 1:
        return None

    current_avg = sum(v for _, v in current_data) / len(current_data)
    previous_avg = sum(v for _, v in previous_data) / len(previous_data)

    delta = current_avg - previous_avg
    if previous_avg == 0:
        delta_pct = Decimal("0")
    else:
        delta_pct = (delta / previous_avg) * Decimal("100")

    return PeriodComparison(
        current_avg=current_avg,
        previous_avg=previous_avg,
        delta=delta,
        delta_pct=delta_pct,
        period_days=period_days,
        price_field=price_field,
    )


def compute_card_analytics(
    prices: list[HistoricalPrice],
    source: str,
    external_id: str,
    price_field: str = "median_price",
    period_days: int | None = None,
) -> CardAnalytics:
    """Orchestrator: compute all indicators and assemble CardAnalytics.

    When ``period_days`` is set, volatility and momentum use that period,
    and performance/period_comparison are computed. When None, uses
    existing defaults (30d volatility, 7d momentum, no performance/comparison).
    Extremes are always computed over the full dataset.
    """
    moving_averages = compute_all_moving_averages(
        prices, periods=[7, 30, 90], price_field=price_field
    )
    # Extremes always over full dataset
    extremes = compute_price_extremes(prices, price_field=price_field)

    vol_period = period_days if period_days is not None else 30
    mom_period = period_days if period_days is not None else 7

    volatility = compute_volatility(prices, period_days=vol_period, price_field=price_field)
    momentum = compute_momentum(prices, period_days=mom_period, price_field=price_field)

    performance = None
    period_comparison = None
    if period_days is not None:
        performance = compute_performance_score(
            prices, period_days=period_days, price_field=price_field
        )
        period_comparison = compute_period_comparison(
            prices, period_days=period_days, price_field=price_field
        )

    return CardAnalytics(
        external_id=external_id,
        source=source,
        moving_averages=moving_averages,
        extremes=extremes,
        volatility=volatility,
        momentum=momentum,
        performance=performance,
        period_comparison=period_comparison,
        computed_at=datetime.now(),
    )
