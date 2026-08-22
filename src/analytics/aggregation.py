"""Pure aggregation functions for price history data.

All functions are pure -- no database imports, no side effects.
Groups daily observations into weekly resolution for longer periods.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from src.api.schemas.cards import PriceChangeSummary, PriceObservation

# Shared constant: maps period string to number of days.
PERIOD_MAP: dict[str, int] = {
    "24h": 1,
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "180d": 180,
    "1y": 365,
}


def determine_resolution(period: str) -> str:
    """Return 'daily' for periods <= 90d, 'weekly' for longer."""
    days = PERIOD_MAP.get(period, 0)
    if days > 90:
        return "weekly"
    return "daily"


def _avg_non_none(values: list[Decimal | None]) -> Decimal | None:
    """Average of non-None Decimal values, or None if all are None."""
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)


def _last_non_none(values: list[int | None]) -> int | None:
    """Return the last non-None value, or None."""
    for v in reversed(values):
        if v is not None:
            return v
    return None


def aggregate_weekly(
    observations: list[PriceObservation],
) -> list[PriceObservation]:
    """Group observations by ISO week.

    For each week, produce one data point:
    - observed_at: last date in the group
    - median_price: average of non-None median_price values
    - tcg_price: average of non-None tcg_price values
    - last_sold_price: average of non-None last_sold_price values
    - quantity_available: last non-None value in the group
    - currency: from first observation
    """
    if not observations:
        return []

    # Group by (year, iso_week)
    groups: dict[tuple[int, int], list[PriceObservation]] = defaultdict(list)
    for obs in observations:
        iso = obs.observed_at.isocalendar()
        key = (iso[0], iso[1])  # (year, week)
        groups[key].append(obs)

    currency = observations[0].currency

    result: list[PriceObservation] = []
    for _key, group in sorted(groups.items()):
        # Sort group by date to get last date
        group.sort(key=lambda o: o.observed_at)

        result.append(
            PriceObservation(
                observed_at=group[-1].observed_at,
                median_price=_avg_non_none([o.median_price for o in group]),
                tcg_price=_avg_non_none([o.tcg_price for o in group]),
                last_sold_price=_avg_non_none([o.last_sold_price for o in group]),
                quantity_available=_last_non_none([o.quantity_available for o in group]),
                currency=currency,
            )
        )

    return result


def aggregate_series(
    observations: list[PriceObservation],
    period: str,
) -> tuple[list[PriceObservation], str]:
    """Apply aggregation based on period.

    Returns (aggregated_observations, resolution_string).
    """
    resolution = determine_resolution(period)
    if resolution == "weekly":
        return aggregate_weekly(observations), resolution
    return observations, resolution


def compute_price_change_summary(
    observations: list[PriceObservation],
    period: str,
    resolution: str,
) -> PriceChangeSummary:
    """Compute start/end price and change metrics.

    - price_start: median_price of first observation
    - price_end: median_price of last observation
    - absolute_change: price_end - price_start
    - percent_change: ((price_end - price_start) / price_start) * 100
    """

    if not observations:
        return PriceChangeSummary(
            period=period,
            data_points=0,
            resolution=resolution,
        )

    price_start = observations[0].median_price
    price_end = observations[-1].median_price

    absolute_change: float | None = None
    percent_change: float | None = None

    if price_start is not None and price_end is not None:
        start_f = float(price_start)
        end_f = float(price_end)
        absolute_change = round(end_f - start_f, 2)
        if start_f != 0:
            percent_change = round(((end_f - start_f) / start_f) * 100, 2)

    return PriceChangeSummary(
        period=period,
        price_start=float(price_start) if price_start is not None else None,
        price_end=float(price_end) if price_end is not None else None,
        absolute_change=absolute_change,
        percent_change=percent_change,
        data_points=len(observations),
        resolution=resolution,
    )
