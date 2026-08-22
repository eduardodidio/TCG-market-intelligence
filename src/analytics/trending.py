"""Pure trending score functions for TCG price data.

All functions are pure -- no database imports, no side effects.
All price arithmetic uses Decimal exclusively.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.domain.models import TrendingScore


def compute_trending_score(
    card_id: int,
    prices: list[tuple[date, Decimal]],
    period_days: int,
    reference_date: date | None = None,
) -> TrendingScore | None:
    """Compute composite trending score for a single card's price series.

    Returns None if:
    - fewer than 2 data points
    - start price is zero
    - no price change (exactly 0)
    """
    if len(prices) < 2:
        return None

    # Sort by date ascending, deduplicate by date (keep last)
    by_date: dict[date, Decimal] = {}
    for d, p in sorted(prices, key=lambda x: x[0]):
        by_date[d] = p
    sorted_prices = sorted(by_date.items(), key=lambda x: x[0])

    if len(sorted_prices) < 2:
        return None

    price_start = sorted_prices[0][1]
    price_end = sorted_prices[-1][1]

    if price_start == Decimal("0"):
        return None

    change_abs = price_end - price_start
    change_pct = (change_abs / price_start) * Decimal("100")

    if change_abs == Decimal("0"):
        return None

    direction = "up" if change_abs > Decimal("0") else "down"

    # Consistency: fraction of daily deltas matching overall direction
    deltas = []
    for i in range(1, len(sorted_prices)):
        delta = sorted_prices[i][1] - sorted_prices[i - 1][1]
        deltas.append(delta)

    if deltas:
        if direction == "up":
            matching = sum(1 for d in deltas if d > Decimal("0"))
        else:
            matching = sum(1 for d in deltas if d < Decimal("0"))
        consistency = Decimal(str(matching)) / Decimal(str(len(deltas)))
    else:
        consistency = Decimal("0")

    observation_count = len(sorted_prices)
    observation_density = min(
        Decimal(str(observation_count)) / Decimal(str(period_days)),
        Decimal("1"),
    )

    latest_date = sorted_prices[-1][0]

    # Recency bonus
    ref = reference_date or date.today()
    days_since = (ref - latest_date).days
    if days_since <= 2:
        recency_bonus = Decimal("1")
    elif days_since <= 7:
        recency_bonus = Decimal("0.5")
    else:
        recency_bonus = Decimal("0")

    # Composite score
    change_component = min(abs(change_pct), Decimal("100")) * Decimal("0.40")
    consistency_component = consistency * Decimal("100") * Decimal("0.30")
    density_component = observation_density * Decimal("100") * Decimal("0.20")
    recency_component = recency_bonus * Decimal("100") * Decimal("0.10")

    composite_score = (
        change_component + consistency_component + density_component + recency_component
    )
    composite_score = min(Decimal("100"), max(Decimal("0"), composite_score))

    return TrendingScore(
        card_id=card_id,
        change_pct=change_pct,
        change_abs=change_abs,
        consistency=consistency,
        observation_count=observation_count,
        observation_density=observation_density,
        composite_score=composite_score,
        direction=direction,
        price_start=price_start,
        price_end=price_end,
        latest_date=latest_date,
    )


def rank_trending(
    scores: list[TrendingScore],
    direction: str,
    min_observations: int = 3,
    min_price: Decimal = Decimal("1.00"),
    min_consistency: Decimal = Decimal("0.50"),
    limit: int = 20,
) -> list[TrendingScore]:
    """Filter and rank trending cards by composite score.

    Anti-false-trending filters:
    - Only cards matching the requested direction
    - min_observations: exclude cards with too few data points
    - min_price: exclude penny-card noise (check price_start for "up", price_end for "down")
    - min_consistency: exclude inconsistent zig-zag movement
    """
    filtered = []
    for s in scores:
        if s.direction != direction:
            continue
        if s.observation_count < min_observations:
            continue
        # Penny-card filter: for gainers check start price, for losers check end price
        price_check = s.price_start if direction == "up" else s.price_end
        if price_check < min_price:
            continue
        if s.consistency < min_consistency:
            continue
        filtered.append(s)

    filtered.sort(key=lambda s: s.composite_score, reverse=True)
    return filtered[:limit]
