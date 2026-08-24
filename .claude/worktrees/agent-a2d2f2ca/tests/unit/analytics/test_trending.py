"""Tests for compute_trending_score() and rank_trending() -- F36."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from src.analytics.trending import compute_trending_score, rank_trending
from src.domain.models import TrendingScore


def _ref() -> date:
    """Fixed reference date for deterministic tests."""
    return date(2026, 8, 22)


def _prices_rising(
    n: int = 10,
    start: Decimal = Decimal("10"),
    step: Decimal = Decimal("1"),
) -> list[tuple[date, Decimal]]:
    """Generate consistently rising prices."""
    ref = _ref()
    return [(ref - timedelta(days=n - i), start + step * i) for i in range(n)]


def _prices_falling(
    n: int = 10,
    start: Decimal = Decimal("20"),
    step: Decimal = Decimal("1"),
) -> list[tuple[date, Decimal]]:
    """Generate consistently falling prices."""
    ref = _ref()
    return [(ref - timedelta(days=n - i), start - step * i) for i in range(n)]


def _prices_flat(
    n: int = 10,
    price: Decimal = Decimal("10"),
) -> list[tuple[date, Decimal]]:
    ref = _ref()
    return [(ref - timedelta(days=n - i), price) for i in range(n)]


class TestComputeTrendingScore:
    def test_returns_none_fewer_than_2_points(self) -> None:
        result = compute_trending_score(1, [(_ref(), Decimal("10"))], 30, _ref())
        assert result is None

    def test_returns_none_empty_list(self) -> None:
        result = compute_trending_score(1, [], 30, _ref())
        assert result is None

    def test_returns_none_zero_start_price(self) -> None:
        prices = [
            (_ref() - timedelta(days=1), Decimal("0")),
            (_ref(), Decimal("10")),
        ]
        result = compute_trending_score(1, prices, 30, _ref())
        assert result is None

    def test_returns_none_no_change(self) -> None:
        prices = _prices_flat(5)
        result = compute_trending_score(1, prices, 30, _ref())
        assert result is None

    def test_direction_up_for_increase(self) -> None:
        prices = _prices_rising(5)
        result = compute_trending_score(1, prices, 30, _ref())
        assert result is not None
        assert result.direction == "up"
        assert result.change_abs > Decimal("0")

    def test_direction_down_for_decrease(self) -> None:
        prices = _prices_falling(5)
        result = compute_trending_score(1, prices, 30, _ref())
        assert result is not None
        assert result.direction == "down"
        assert result.change_abs < Decimal("0")

    def test_change_pct_correct(self) -> None:
        prices = [
            (_ref() - timedelta(days=2), Decimal("10")),
            (_ref() - timedelta(days=1), Decimal("12")),
            (_ref(), Decimal("15")),
        ]
        result = compute_trending_score(1, prices, 30, _ref())
        assert result is not None
        assert result.change_pct == Decimal("50")  # (15-10)/10 * 100

    def test_change_abs_correct(self) -> None:
        prices = [
            (_ref() - timedelta(days=1), Decimal("10")),
            (_ref(), Decimal("15")),
        ]
        result = compute_trending_score(1, prices, 30, _ref())
        assert result is not None
        assert result.change_abs == Decimal("5")

    def test_consistency_all_up(self) -> None:
        prices = _prices_rising(5)
        result = compute_trending_score(1, prices, 30, _ref())
        assert result is not None
        assert result.consistency == Decimal("1")

    def test_consistency_all_down(self) -> None:
        prices = _prices_falling(5)
        result = compute_trending_score(1, prices, 30, _ref())
        assert result is not None
        assert result.consistency == Decimal("1")

    def test_consistency_alternating(self) -> None:
        ref = _ref()
        prices = [
            (ref - timedelta(days=4), Decimal("10")),
            (ref - timedelta(days=3), Decimal("12")),
            (ref - timedelta(days=2), Decimal("11")),
            (ref - timedelta(days=1), Decimal("13")),
            (ref, Decimal("14")),
        ]
        result = compute_trending_score(1, prices, 30, ref)
        assert result is not None
        # direction = up, deltas: +2, -1, +2, +1 -> 3/4 = 0.75
        assert result.consistency == Decimal("0.75")

    def test_observation_density(self) -> None:
        prices = _prices_rising(10)
        result = compute_trending_score(1, prices, 30, _ref())
        assert result is not None
        # 10 / 30 = 0.333...
        expected = Decimal("10") / Decimal("30")
        assert abs(result.observation_density - expected) < Decimal("0.001")

    def test_density_capped_at_one(self) -> None:
        prices = _prices_rising(30)
        result = compute_trending_score(1, prices, 10, _ref())
        assert result is not None
        assert result.observation_density == Decimal("1")

    def test_recency_full_bonus(self) -> None:
        ref = _ref()
        prices = [
            (ref - timedelta(days=5), Decimal("10")),
            (ref - timedelta(days=1), Decimal("15")),
        ]
        result = compute_trending_score(1, prices, 30, ref)
        assert result is not None
        # Latest is 1 day ago <= 2 -> full bonus
        assert result.composite_score > Decimal("0")

    def test_recency_no_bonus(self) -> None:
        ref = _ref()
        prices = [
            (ref - timedelta(days=30), Decimal("10")),
            (ref - timedelta(days=20), Decimal("15")),
        ]
        result = compute_trending_score(1, prices, 30, ref)
        assert result is not None
        # Latest is 20 days ago > 7 -> no bonus

    def test_composite_score_in_range(self) -> None:
        prices = _prices_rising(10)
        result = compute_trending_score(1, prices, 30, _ref())
        assert result is not None
        assert Decimal("0") <= result.composite_score <= Decimal("100")

    def test_deterministic_with_reference_date(self) -> None:
        prices = _prices_rising(5)
        r1 = compute_trending_score(1, prices, 30, _ref())
        r2 = compute_trending_score(1, prices, 30, _ref())
        assert r1 is not None and r2 is not None
        assert r1.composite_score == r2.composite_score

    def test_deduplication_same_date(self) -> None:
        ref = _ref()
        prices = [
            (ref - timedelta(days=2), Decimal("10")),
            (ref - timedelta(days=2), Decimal("8")),
            (ref, Decimal("15")),
        ]
        result = compute_trending_score(1, prices, 30, ref)
        assert result is not None
        # Second observation on same date (8) should override first (10) due to sort
        assert result.observation_count == 2


class TestRankTrending:
    def _make_score(
        self,
        card_id: int,
        direction: str = "up",
        composite: Decimal = Decimal("50"),
        obs: int = 5,
        price_start: Decimal = Decimal("10"),
        price_end: Decimal = Decimal("15"),
        consistency: Decimal = Decimal("0.8"),
    ) -> TrendingScore:
        return TrendingScore(
            card_id=card_id,
            change_pct=Decimal("50"),
            change_abs=Decimal("5"),
            consistency=consistency,
            observation_count=obs,
            observation_density=Decimal("0.5"),
            composite_score=composite,
            direction=direction,
            price_start=price_start,
            price_end=price_end,
            latest_date=_ref(),
        )

    def test_filters_by_direction(self) -> None:
        scores = [
            self._make_score(1, "up"),
            self._make_score(2, "down"),
            self._make_score(3, "up"),
        ]
        result = rank_trending(scores, "up")
        assert len(result) == 2
        assert all(s.direction == "up" for s in result)

    def test_filters_by_min_observations(self) -> None:
        scores = [
            self._make_score(1, "up", obs=2),
            self._make_score(2, "up", obs=5),
        ]
        result = rank_trending(scores, "up", min_observations=3)
        assert len(result) == 1
        assert result[0].card_id == 2

    def test_filters_by_min_price_up(self) -> None:
        scores = [
            self._make_score(1, "up", price_start=Decimal("0.50")),
            self._make_score(2, "up", price_start=Decimal("5.00")),
        ]
        result = rank_trending(scores, "up", min_price=Decimal("1.00"))
        assert len(result) == 1
        assert result[0].card_id == 2

    def test_filters_by_min_price_down(self) -> None:
        scores = [
            self._make_score(1, "down", price_end=Decimal("0.50")),
            self._make_score(2, "down", price_end=Decimal("5.00")),
        ]
        result = rank_trending(scores, "down", min_price=Decimal("1.00"))
        assert len(result) == 1
        assert result[0].card_id == 2

    def test_filters_by_min_consistency(self) -> None:
        scores = [
            self._make_score(1, "up", consistency=Decimal("0.3")),
            self._make_score(2, "up", consistency=Decimal("0.8")),
        ]
        result = rank_trending(scores, "up", min_consistency=Decimal("0.5"))
        assert len(result) == 1
        assert result[0].card_id == 2

    def test_sorts_by_composite_descending(self) -> None:
        scores = [
            self._make_score(1, "up", composite=Decimal("30")),
            self._make_score(2, "up", composite=Decimal("90")),
            self._make_score(3, "up", composite=Decimal("60")),
        ]
        result = rank_trending(scores, "up")
        assert [s.card_id for s in result] == [2, 3, 1]

    def test_applies_limit(self) -> None:
        scores = [self._make_score(i, "up", composite=Decimal(str(i * 10))) for i in range(10)]
        result = rank_trending(scores, "up", limit=3)
        assert len(result) == 3

    def test_returns_empty_when_all_filtered(self) -> None:
        scores = [self._make_score(1, "up", obs=1)]
        result = rank_trending(scores, "up", min_observations=3)
        assert result == []
