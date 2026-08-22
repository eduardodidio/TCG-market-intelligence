"""Pure functions for deck valuation — no DB imports."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from src.domain.models import DeckValuation, DeckValueChange, DeckValuePoint, HistoricalPrice


def compute_deck_value(
    card_prices: dict[int, Decimal | None],
    deck_cards: list,
) -> DeckValuation:
    """Sum card_price * quantity for each deck card with a linked card_id and known price.

    ``deck_cards`` must have ``card_id`` and ``quantity`` attributes.
    Returns DeckValuation with total_value=None if no cards have prices.
    """
    total = Decimal("0")
    priced = 0
    unpriced = 0
    has_any_price = False

    for dc in deck_cards:
        card_id = getattr(dc, "card_id", None)
        quantity = getattr(dc, "quantity", 1)

        if card_id is None:
            unpriced += 1
            continue

        price = card_prices.get(card_id)
        if price is not None:
            total += price * quantity
            priced += 1
            has_any_price = True
        else:
            unpriced += 1

    return DeckValuation(
        total_value=total if has_any_price else None,
        priced_cards=priced,
        unpriced_cards=unpriced,
    )


def compute_deck_value_series(
    deck_cards: list,
    price_series_by_card: dict[int, list[HistoricalPrice]],
    days: int = 90,
) -> list[DeckValuePoint]:
    """Build a date-indexed deck value series by summing all card prices per date.

    Uses carry-forward for gaps: if a card has no observation on a given date,
    the last known price is used.  Downsamples to max 30 points.

    ``deck_cards`` must have ``card_id`` and ``quantity`` attributes.
    """
    # Collect card_ids that are linked and have price data
    card_qty: dict[int, int] = {}
    for dc in deck_cards:
        cid = getattr(dc, "card_id", None)
        if cid is not None and cid in price_series_by_card:
            card_qty[cid] = card_qty.get(cid, 0) + getattr(dc, "quantity", 1)

    if not card_qty:
        return []

    # Build per-card date->price mapping
    card_date_price: dict[int, dict[date, Decimal]] = defaultdict(dict)
    all_dates: set[date] = set()

    for cid, series in price_series_by_card.items():
        if cid not in card_qty:
            continue
        for obs in series:
            price = obs.median_price
            if price is not None:
                obs_date = obs.observed_at if isinstance(obs.observed_at, date) else obs.observed_at
                card_date_price[cid][obs_date] = price
                all_dates.add(obs_date)

    if not all_dates:
        return []

    sorted_dates = sorted(all_dates)

    # Build value series with carry-forward
    result: list[DeckValuePoint] = []
    last_known: dict[int, Decimal] = {}

    for d in sorted_dates:
        day_total = Decimal("0")
        has_value = False

        for cid, qty in card_qty.items():
            if d in card_date_price.get(cid, {}):
                last_known[cid] = card_date_price[cid][d]

            if cid in last_known:
                day_total += last_known[cid] * qty
                has_value = True

        if has_value:
            result.append(DeckValuePoint(date=d, total_value=day_total))

    # Downsample to max 30 points
    if len(result) > 30:
        step = len(result) / 30
        indices = [int(i * step) for i in range(30)]
        # Always include last point
        if indices[-1] != len(result) - 1:
            indices[-1] = len(result) - 1
        result = [result[i] for i in indices]

    return result


def compute_deck_value_change(
    value_series: list[DeckValuePoint],
    period_days: int,
) -> DeckValueChange | None:
    """Compare last value to the value ``period_days`` ago.

    Returns None if fewer than 2 data points.
    """
    if len(value_series) < 2:
        return None

    current_point = value_series[-1]
    target_date = current_point.date - timedelta(days=period_days)

    # Find the closest point to target_date (at or before)
    previous_point = value_series[0]
    for point in value_series:
        if point.date <= target_date:
            previous_point = point
        else:
            break

    current = current_point.total_value
    previous = previous_point.total_value

    delta = current - previous
    delta_pct = (
        (delta / previous * Decimal("100")).quantize(Decimal("0.01"))
        if previous != 0
        else Decimal("0")
    )

    return DeckValueChange(
        current=current,
        previous=previous,
        delta=delta,
        delta_pct=delta_pct,
    )
