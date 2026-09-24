"""Tests for scripts/diagnose_trending_f175.py.

Covers the pure `summarize` helper and the CLI argument validation.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.diagnose_trending_f175 import main, summarize


def _dates_back(n: int) -> list[date]:
    today = date.today()
    return [today - timedelta(days=i) for i in range(n)]


class TestSummarize:
    def test_happy_path_counts_gainer(self):
        d0, d1, d2 = sorted(_dates_back(3))
        price_data = {
            1: [(d0, Decimal("10.00")), (d1, Decimal("12.00")), (d2, Decimal("15.00"))],
            2: [(d0, Decimal("10.00")), (d1, Decimal("9.00")), (d2, Decimal("8.00"))],
            3: [(d0, Decimal("5.00"))],
        }

        result = summarize(price_data, days=30)

        assert result["days"] == 30
        assert result["cards"] == 3
        assert result["points"] == 7
        assert result["gainers"] == 1
        assert result["losers"] == 1

    def test_empty_price_data_is_zero(self):
        result = summarize({}, days=7)

        assert result == {
            "days": 7,
            "cards": 0,
            "points": 0,
            "scored": 0,
            "gainers": 0,
            "losers": 0,
        }

    def test_card_with_exactly_min_observations_is_ranked(self):
        """min_observations=3 in rank_trending: a card with exactly 3 dates counts."""
        d0, d1, d2 = sorted(_dates_back(3))
        price_data = {
            1: [(d0, Decimal("10.00")), (d1, Decimal("11.00")), (d2, Decimal("12.00"))],
        }

        result = summarize(price_data, days=30)

        assert result["scored"] == 1
        assert result["gainers"] == 1


class TestMain:
    def test_invalid_days_zero_errors(self):
        exit_code = None
        try:
            main(["--days", "0"])
        except SystemExit as exc:
            exit_code = exc.code
        assert exit_code not in (0, None)

    def test_invalid_days_negative_errors(self):
        exit_code = None
        try:
            main(["--days", "-5"])
        except SystemExit as exc:
            exit_code = exc.code
        assert exit_code not in (0, None)
