"""Tests for src/marketplace/fees.py — trade fee calculator."""

from decimal import Decimal

import pytest

from src.marketplace.fees import DEFAULT_FEE, FEE_TIERS, calculate_trade_fee


class TestCalculateTradeFee:
    """Every tier boundary from the task spec is tested explicitly."""

    # --- None / invalid prices → minimum fee (2) ---

    def test_none_returns_minimum_fee(self):
        assert calculate_trade_fee(None) == 2

    def test_zero_returns_minimum_fee(self):
        assert calculate_trade_fee(Decimal("0")) == 2

    def test_negative_returns_minimum_fee(self):
        assert calculate_trade_fee(Decimal("-5.00")) == 2

    # --- Tier 1: 0 < price <= 10.00 → 2 credits ---

    def test_small_price_in_tier_1(self):
        assert calculate_trade_fee(Decimal("5.00")) == 2

    def test_tier_1_upper_boundary(self):
        assert calculate_trade_fee(Decimal("10.00")) == 2

    def test_penny_above_zero(self):
        assert calculate_trade_fee(Decimal("0.01")) == 2

    # --- Tier 2: 10.01–50.00 → 3 credits ---

    def test_just_above_tier_1(self):
        assert calculate_trade_fee(Decimal("10.01")) == 3

    def test_tier_2_upper_boundary(self):
        assert calculate_trade_fee(Decimal("50.00")) == 3

    def test_tier_2_midpoint(self):
        assert calculate_trade_fee(Decimal("30.00")) == 3

    # --- Tier 3: 50.01–100.00 → 5 credits ---

    def test_just_above_tier_2(self):
        assert calculate_trade_fee(Decimal("50.01")) == 5

    def test_tier_3_upper_boundary(self):
        assert calculate_trade_fee(Decimal("100.00")) == 5

    # --- Tier 4: 100.01–150.00 → 8 credits ---

    def test_just_above_tier_3(self):
        assert calculate_trade_fee(Decimal("100.01")) == 8

    def test_tier_4_upper_boundary(self):
        assert calculate_trade_fee(Decimal("150.00")) == 8

    # --- Tier 5: 150.01–200.00 → 13 credits ---

    def test_just_above_tier_4(self):
        assert calculate_trade_fee(Decimal("150.01")) == 13

    def test_tier_5_upper_boundary(self):
        assert calculate_trade_fee(Decimal("200.00")) == 13

    # --- Tier 6: 200.01–500.00 → 21 credits ---

    def test_just_above_tier_5(self):
        assert calculate_trade_fee(Decimal("200.01")) == 21

    def test_tier_6_upper_boundary(self):
        assert calculate_trade_fee(Decimal("500.00")) == 21

    # --- Default: > 500.00 → 50 credits ---

    def test_just_above_tier_6(self):
        assert calculate_trade_fee(Decimal("500.01")) == 50

    def test_very_high_price(self):
        assert calculate_trade_fee(Decimal("9999.99")) == 50

    # --- Constants sanity checks ---

    def test_default_fee_value(self):
        assert DEFAULT_FEE == 50

    def test_fee_tiers_ascending_prices(self):
        prices = [t[0] for t in FEE_TIERS]
        assert prices == sorted(prices)

    def test_fee_tiers_ascending_fees(self):
        fees = [t[1] for t in FEE_TIERS]
        assert fees == sorted(fees)

    def test_fee_tiers_count(self):
        assert len(FEE_TIERS) == 6


class TestCalculateTradeFeeParametrized:
    """Parametrized sweep across all boundaries for compact coverage."""

    @pytest.mark.parametrize(
        "price, expected_fee",
        [
            (None, 2),
            (Decimal("0"), 2),
            (Decimal("-1"), 2),
            (Decimal("0.01"), 2),
            (Decimal("9.99"), 2),
            (Decimal("10.00"), 2),
            (Decimal("10.01"), 3),
            (Decimal("25.00"), 3),
            (Decimal("50.00"), 3),
            (Decimal("50.01"), 5),
            (Decimal("75.00"), 5),
            (Decimal("100.00"), 5),
            (Decimal("100.01"), 8),
            (Decimal("125.00"), 8),
            (Decimal("150.00"), 8),
            (Decimal("150.01"), 13),
            (Decimal("175.00"), 13),
            (Decimal("200.00"), 13),
            (Decimal("200.01"), 21),
            (Decimal("350.00"), 21),
            (Decimal("500.00"), 21),
            (Decimal("500.01"), 50),
            (Decimal("1000.00"), 50),
            (Decimal("9999.99"), 50),
        ],
    )
    def test_fee_for_price(self, price, expected_fee):
        assert calculate_trade_fee(price) == expected_fee
