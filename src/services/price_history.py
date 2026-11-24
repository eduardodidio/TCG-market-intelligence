"""Price history service — unified access to card price history and diagnostics.

Wraps :mod:`src.services.collection_price_history` to provide:

- ``get_price_history(repo, card_id, is_foil, days)`` — merged price series
  plus metadata (variant, sources, real/snapshot point counts).
- ``get_price_diagnostics(repo, card_id, is_foil, days)`` — min/max/avg/trend
  summary computed from the merged history.

These are consumed by the ``/api/v1/price-history/`` router (F213-T07).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from src.database.repository import Repository
from src.domain.models import HistoricalPrice
from src.services.collection_price_history import build_history


def get_price_history(
    repo: Repository,
    card_id: int,
    is_foil: bool = False,
    days: int | None = 90,
    today: date | None = None,
) -> tuple[list[HistoricalPrice], dict[str, Any]]:
    """Return the merged price history for *card_id* plus metadata.

    Delegates to :func:`build_history` which handles key resolution,
    series loading, and per-day merge.

    Returns:
        ``(observations, meta)`` where *meta* is a dict with keys
        ``variant``, ``sources``, ``first_observed_at``, ``last_observed_at``,
        ``real_points``, ``snapshot_points``.
    """
    return build_history(repo, card_id, is_foil=is_foil, days=days, today=today)


def get_price_diagnostics(
    repo: Repository,
    card_id: int,
    is_foil: bool = False,
    days: int | None = 90,
    today: date | None = None,
) -> dict[str, Any]:
    """Compute summary statistics from the merged price history.

    Returns a dict with:
        - ``min_price``, ``max_price``, ``avg_price`` (float | None)
        - ``current_price`` (float | None) — last observation
        - ``data_points`` (int)
        - ``trend`` ("up" | "down" | "stable" | None)
        - ``change_pct`` (float | None) — % change first→last
        - Plus all keys from :func:`get_price_history` meta.
    """
    observations, meta = get_price_history(repo, card_id, is_foil=is_foil, days=days, today=today)

    prices = [float(o.median_price) for o in observations if o.median_price is not None]

    if not prices:
        return {
            **meta,
            "min_price": None,
            "max_price": None,
            "avg_price": None,
            "current_price": None,
            "data_points": 0,
            "trend": None,
            "change_pct": None,
        }

    min_price = min(prices)
    max_price = max(prices)
    avg_price = round(sum(prices) / len(prices), 2)
    current_price = prices[-1]

    # Trend: compare first and last price
    change_pct: float | None = None
    trend: str | None = None
    if len(prices) >= 2:
        first = prices[0]
        last = prices[-1]
        if first != 0:
            change_pct = round(((last - first) / first) * 100, 1)
        else:
            change_pct = 0.0

        if change_pct > 1.0:
            trend = "up"
        elif change_pct < -1.0:
            trend = "down"
        else:
            trend = "stable"

    return {
        **meta,
        "min_price": min_price,
        "max_price": max_price,
        "avg_price": avg_price,
        "current_price": current_price,
        "data_points": len(prices),
        "trend": trend,
        "change_pct": change_pct,
    }
