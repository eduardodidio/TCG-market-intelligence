"""Tests for F185-T01: get_movers() sanity filters (price floor + pct cap)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from src.database.models import Base, CardRow, PriceObservationRow, SourceCardRow
from src.database.repository import Repository


@pytest.fixture()
def repo():
    """In-memory SQLite repository for movers tests."""
    r = Repository(db_url="sqlite:///:memory:")
    Base.metadata.create_all(r.engine)
    return r


def _seed_card(session: Session, card_id: int, name: str = "") -> None:
    session.add(
        CardRow(
            id=card_id,
            game="magic",
            name_en=name or f"Card {card_id}",
            set_code="TST",
            collector_number=str(card_id).zfill(3),
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )
    )


def _seed_source_card(session: Session, card_id: int) -> None:
    ext_id = f"liga_{card_id}"
    session.add(
        SourceCardRow(
            source="liga",
            external_id=ext_id,
            card_id=card_id,
            url=f"https://example.com/{ext_id}",
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )
    )


def _seed_prices(
    session: Session,
    card_id: int,
    price_start: Decimal,
    price_end: Decimal,
    days_ago: int = 5,
) -> None:
    """Seed earliest (days_ago) and latest (today) price observations."""
    ext_id = f"liga_{card_id}"
    today = date.today()
    start_date = today - timedelta(days=days_ago)
    session.add(
        PriceObservationRow(
            source="liga",
            external_id=ext_id,
            observed_at=start_date,
            median_price=price_start,
        )
    )
    session.add(
        PriceObservationRow(
            source="liga",
            external_id=ext_id,
            observed_at=today,
            median_price=price_end,
        )
    )


def _seed_full_card(
    session: Session,
    card_id: int,
    price_start: Decimal,
    price_end: Decimal,
    name: str = "",
) -> None:
    """Seed a card with source_card and two price observations."""
    _seed_card(session, card_id, name)
    _seed_source_card(session, card_id)
    _seed_prices(session, card_id, price_start, price_end)


class TestMoversMinimumPriceFloor:
    """Cards below R$0.50 price_start should be excluded."""

    def test_low_price_excluded(self, repo):
        """Card with price_start=0.10 is excluded from movers."""
        with Session(repo.engine) as session:
            _seed_full_card(session, 1, Decimal("0.10"), Decimal("1.00"))
            session.commit()

        gainers, losers = repo.get_movers(days=7, limit=10)
        all_ids = [m[0] for m in gainers + losers]
        assert 1 not in all_ids

    def test_price_at_threshold_included(self, repo):
        """Card with price_start=0.50 is included in movers."""
        with Session(repo.engine) as session:
            _seed_full_card(session, 1, Decimal("0.50"), Decimal("1.00"))
            session.commit()

        gainers, losers = repo.get_movers(days=7, limit=10)
        all_ids = [m[0] for m in gainers + losers]
        assert 1 in all_ids

    def test_price_below_threshold_at_049(self, repo):
        """Card with price_start=0.49 is excluded (below 0.50 floor)."""
        with Session(repo.engine) as session:
            _seed_full_card(session, 1, Decimal("0.49"), Decimal("2.00"))
            session.commit()

        gainers, losers = repo.get_movers(days=7, limit=10)
        all_ids = [m[0] for m in gainers + losers]
        assert 1 not in all_ids


class TestMoversPercentageCap:
    """Movers with abs(change_pct) > 1000% should be excluded."""

    def test_extreme_positive_pct_excluded(self, repo):
        """Card with ~5000% change is excluded."""
        with Session(repo.engine) as session:
            # price_start=1.00 -> price_end=51.00 => (51-1)/1*100 = 5000%
            _seed_full_card(session, 1, Decimal("1.00"), Decimal("51.00"))
            session.commit()

        gainers, losers = repo.get_movers(days=7, limit=10)
        all_ids = [m[0] for m in gainers + losers]
        assert 1 not in all_ids

    def test_normal_pct_included(self, repo):
        """Card with 50% change is included."""
        with Session(repo.engine) as session:
            # price_start=1.00 -> price_end=1.50 => 50%
            _seed_full_card(session, 1, Decimal("1.00"), Decimal("1.50"))
            session.commit()

        gainers, losers = repo.get_movers(days=7, limit=10)
        all_ids = [m[0] for m in gainers + losers]
        assert 1 in all_ids

    def test_boundary_1000_pct_included(self, repo):
        """Card with exactly 1000% change is included (boundary)."""
        with Session(repo.engine) as session:
            # price_start=1.00 -> price_end=11.00 => (11-1)/1*100 = 1000%
            _seed_full_card(session, 1, Decimal("1.00"), Decimal("11.00"))
            session.commit()

        gainers, losers = repo.get_movers(days=7, limit=10)
        all_ids = [m[0] for m in gainers + losers]
        assert 1 in all_ids

    def test_boundary_1001_pct_excluded(self, repo):
        """Card with 1001% change is excluded (just over boundary)."""
        with Session(repo.engine) as session:
            # price_start=1.00 -> price_end=11.01 => (11.01-1)/1*100 = 1001%
            _seed_full_card(session, 1, Decimal("1.00"), Decimal("11.01"))
            session.commit()

        gainers, losers = repo.get_movers(days=7, limit=10)
        all_ids = [m[0] for m in gainers + losers]
        assert 1 not in all_ids

    def test_negative_boundary_minus_1000_included(self, repo):
        """Card with -1000% is impossible in practice (price can't go below 0).

        Instead test a large negative like -90% is included.
        A -1000% would require price_end = price_start * (1 - 10) = negative,
        so we test the realistic maximum negative: -90%.
        """
        with Session(repo.engine) as session:
            # price_start=10.00 -> price_end=1.00 => (1-10)/10*100 = -90%
            _seed_full_card(session, 1, Decimal("10.00"), Decimal("1.00"))
            session.commit()

        gainers, losers = repo.get_movers(days=7, limit=10)
        all_ids = [m[0] for m in gainers + losers]
        assert 1 in all_ids


class TestMoversHappyPath:
    """Regression: normal movers behavior still works."""

    def test_gainers_sorted_descending(self, repo):
        """Gainers are sorted by change_pct descending."""
        with Session(repo.engine) as session:
            # Card 1: 100% gain, Card 2: 50% gain
            _seed_full_card(session, 1, Decimal("1.00"), Decimal("2.00"), "Big Gainer")
            _seed_full_card(session, 2, Decimal("2.00"), Decimal("3.00"), "Small Gainer")
            session.commit()

        gainers, losers = repo.get_movers(days=7, limit=10)
        assert len(gainers) == 2
        assert gainers[0][0] == 1  # 100% > 50%
        assert gainers[1][0] == 2

    def test_losers_sorted_ascending(self, repo):
        """Losers are sorted by change_pct ascending (most negative first)."""
        with Session(repo.engine) as session:
            # Card 1: -50% loss, Card 2: -25% loss
            _seed_full_card(session, 1, Decimal("2.00"), Decimal("1.00"), "Big Loser")
            _seed_full_card(session, 2, Decimal("4.00"), Decimal("3.00"), "Small Loser")
            session.commit()

        gainers, losers = repo.get_movers(days=7, limit=10)
        assert len(losers) == 2
        assert losers[0][0] == 1  # -50% < -25%

    def test_both_filters_combined(self, repo):
        """Only cards passing both filters appear in results."""
        with Session(repo.engine) as session:
            # Card 1: good (price_start=1.00, 50% change)
            _seed_full_card(session, 1, Decimal("1.00"), Decimal("1.50"), "Good Card")
            # Card 2: bad price floor (price_start=0.10, huge % change)
            _seed_full_card(session, 2, Decimal("0.10"), Decimal("1.00"), "Low Price")
            # Card 3: bad pct cap (price_start=1.00, 5000% change)
            _seed_full_card(session, 3, Decimal("1.00"), Decimal("51.00"), "Extreme Pct")
            session.commit()

        gainers, losers = repo.get_movers(days=7, limit=10)
        all_ids = [m[0] for m in gainers + losers]
        assert 1 in all_ids
        assert 2 not in all_ids
        assert 3 not in all_ids
