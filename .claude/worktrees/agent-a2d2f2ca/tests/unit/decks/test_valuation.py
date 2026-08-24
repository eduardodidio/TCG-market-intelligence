"""Tests for deck valuation pure functions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from src.decks.valuation import (
    compute_deck_value,
    compute_deck_value_change,
    compute_deck_value_series,
)
from src.domain.models import DeckValuePoint, HistoricalPrice


@dataclass
class FakeDeckCard:
    card_id: int | None
    quantity: int = 1


# ---------------------------------------------------------------------------
# compute_deck_value
# ---------------------------------------------------------------------------


class TestComputeDeckValue:
    def test_basic_sum(self):
        prices = {1: Decimal("10.00"), 2: Decimal("5.50"), 3: Decimal("2.25")}
        cards = [
            FakeDeckCard(card_id=1, quantity=4),
            FakeDeckCard(card_id=2, quantity=2),
            FakeDeckCard(card_id=3, quantity=1),
        ]
        result = compute_deck_value(prices, cards)
        # 10*4 + 5.5*2 + 2.25*1 = 40 + 11 + 2.25 = 53.25
        assert result.total_value == Decimal("53.25")
        assert result.priced_cards == 3
        assert result.unpriced_cards == 0

    def test_mixed_priced_unpriced(self):
        prices = {1: Decimal("10.00"), 2: None}
        cards = [
            FakeDeckCard(card_id=1, quantity=1),
            FakeDeckCard(card_id=2, quantity=1),
            FakeDeckCard(card_id=None, quantity=1),  # unlinked
        ]
        result = compute_deck_value(prices, cards)
        assert result.total_value == Decimal("10.00")
        assert result.priced_cards == 1
        assert result.unpriced_cards == 2

    def test_all_unpriced(self):
        prices = {1: None, 2: None}
        cards = [
            FakeDeckCard(card_id=1, quantity=1),
            FakeDeckCard(card_id=2, quantity=1),
        ]
        result = compute_deck_value(prices, cards)
        assert result.total_value is None
        assert result.priced_cards == 0
        assert result.unpriced_cards == 2

    def test_empty_deck(self):
        result = compute_deck_value({}, [])
        assert result.total_value is None
        assert result.priced_cards == 0
        assert result.unpriced_cards == 0

    def test_unlinked_cards(self):
        prices = {1: Decimal("5.00")}
        cards = [
            FakeDeckCard(card_id=1, quantity=2),
            FakeDeckCard(card_id=None, quantity=3),
        ]
        result = compute_deck_value(prices, cards)
        assert result.total_value == Decimal("10.00")
        assert result.priced_cards == 1
        assert result.unpriced_cards == 1

    def test_card_not_in_prices_dict(self):
        """A linked card whose card_id is not in the prices dict counts as unpriced."""
        prices = {1: Decimal("5.00")}
        cards = [
            FakeDeckCard(card_id=1, quantity=1),
            FakeDeckCard(card_id=999, quantity=1),  # not in prices dict
        ]
        result = compute_deck_value(prices, cards)
        assert result.total_value == Decimal("5.00")
        assert result.priced_cards == 1
        assert result.unpriced_cards == 1


# ---------------------------------------------------------------------------
# compute_deck_value_series
# ---------------------------------------------------------------------------


def _hp(card_id: int, d: date, price: Decimal) -> HistoricalPrice:
    return HistoricalPrice(
        source="test",
        external_id=f"ext_{card_id}",
        observed_at=d,
        median_price=price,
    )


class TestComputeDeckValueSeries:
    def test_single_card(self):
        today = date.today()
        cards = [FakeDeckCard(card_id=1, quantity=2)]
        series = {
            1: [
                _hp(1, today - timedelta(days=2), Decimal("5.00")),
                _hp(1, today - timedelta(days=1), Decimal("6.00")),
                _hp(1, today, Decimal("7.00")),
            ]
        }
        result = compute_deck_value_series(cards, series, days=7)
        assert len(result) == 3
        assert result[0].total_value == Decimal("10.00")
        assert result[2].total_value == Decimal("14.00")

    def test_multiple_cards_summed(self):
        today = date.today()
        cards = [
            FakeDeckCard(card_id=1, quantity=1),
            FakeDeckCard(card_id=2, quantity=1),
        ]
        series = {
            1: [_hp(1, today, Decimal("10.00"))],
            2: [_hp(2, today, Decimal("5.00"))],
        }
        result = compute_deck_value_series(cards, series, days=7)
        assert len(result) == 1
        assert result[0].total_value == Decimal("15.00")

    def test_carry_forward(self):
        """If card B has no observation on day 1, carry-forward from earlier."""
        d0 = date.today() - timedelta(days=3)
        d1 = date.today() - timedelta(days=2)
        d2 = date.today() - timedelta(days=1)

        cards = [
            FakeDeckCard(card_id=1, quantity=1),
            FakeDeckCard(card_id=2, quantity=1),
        ]
        series = {
            1: [
                _hp(1, d0, Decimal("10.00")),
                _hp(1, d1, Decimal("11.00")),
                _hp(1, d2, Decimal("12.00")),
            ],
            2: [_hp(2, d0, Decimal("5.00")), _hp(2, d2, Decimal("7.00"))],
            # card 2 has no observation on d1 — should carry forward 5.00
        }
        result = compute_deck_value_series(cards, series, days=7)
        # d0: 10+5=15, d1: 11+5=16 (carry-forward), d2: 12+7=19
        assert len(result) == 3
        assert result[0].total_value == Decimal("15.00")
        assert result[1].total_value == Decimal("16.00")
        assert result[2].total_value == Decimal("19.00")

    def test_downsampling(self):
        """Series with >30 points should be downsampled to 30."""
        cards = [FakeDeckCard(card_id=1, quantity=1)]
        today = date.today()
        series = {
            1: [_hp(1, today - timedelta(days=i), Decimal("10.00")) for i in range(60, 0, -1)]
        }
        result = compute_deck_value_series(cards, series, days=90)
        assert len(result) == 30

    def test_empty_input(self):
        result = compute_deck_value_series([], {}, days=30)
        assert result == []

    def test_no_linked_cards(self):
        cards = [FakeDeckCard(card_id=None, quantity=1)]
        series = {1: [_hp(1, date.today(), Decimal("10.00"))]}
        result = compute_deck_value_series(cards, series, days=30)
        assert result == []


# ---------------------------------------------------------------------------
# compute_deck_value_change
# ---------------------------------------------------------------------------


class TestComputeDeckValueChange:
    def test_positive_change(self):
        today = date.today()
        series = [
            DeckValuePoint(date=today - timedelta(days=30), total_value=Decimal("100.00")),
            DeckValuePoint(date=today, total_value=Decimal("120.00")),
        ]
        result = compute_deck_value_change(series, 30)
        assert result is not None
        assert result.current == Decimal("120.00")
        assert result.previous == Decimal("100.00")
        assert result.delta == Decimal("20.00")
        assert result.delta_pct == Decimal("20.00")

    def test_negative_change(self):
        today = date.today()
        series = [
            DeckValuePoint(date=today - timedelta(days=7), total_value=Decimal("100.00")),
            DeckValuePoint(date=today, total_value=Decimal("80.00")),
        ]
        result = compute_deck_value_change(series, 7)
        assert result is not None
        assert result.delta == Decimal("-20.00")
        assert result.delta_pct == Decimal("-20.00")

    def test_insufficient_data(self):
        series = [DeckValuePoint(date=date.today(), total_value=Decimal("100.00"))]
        result = compute_deck_value_change(series, 30)
        assert result is None

    def test_empty_series(self):
        result = compute_deck_value_change([], 30)
        assert result is None

    def test_period_exceeds_data(self):
        """When period_days exceeds available data, use earliest point."""
        today = date.today()
        series = [
            DeckValuePoint(date=today - timedelta(days=5), total_value=Decimal("90.00")),
            DeckValuePoint(date=today, total_value=Decimal("100.00")),
        ]
        # Ask for 30 days but only 5 days of data
        result = compute_deck_value_change(series, 30)
        assert result is not None
        assert result.previous == Decimal("90.00")
        assert result.current == Decimal("100.00")

    def test_zero_previous_value(self):
        today = date.today()
        series = [
            DeckValuePoint(date=today - timedelta(days=7), total_value=Decimal("0")),
            DeckValuePoint(date=today, total_value=Decimal("50.00")),
        ]
        result = compute_deck_value_change(series, 7)
        assert result is not None
        assert result.delta == Decimal("50.00")
        assert result.delta_pct == Decimal("0")  # division by zero handled
