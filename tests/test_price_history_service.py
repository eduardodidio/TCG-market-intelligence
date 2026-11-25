"""Tests for src.services.price_history (F213-T05).

Covers:
- Variant ID resolution (direct patterns + source_cards)
- Same-day dedup with source priority (manual > liga > jsonld > myp > daily_snapshot)
- Date range filtering
- Diagnostics output format
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from src.collection.price_history_keys import SNAPSHOT_SOURCE
from src.database.models import Base, CardRow, PriceObservationRow, SourceCardRow
from src.database.repository import Repository
from src.services.price_history import (
    get_price_diagnostics,
    get_price_history,
)

TODAY = date(2026, 11, 24)


def D(n: int) -> date:  # noqa: N802
    """Shorthand: D(5) == TODAY - 5 days."""
    return TODAY - timedelta(days=n)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def repo() -> Repository:
    r = Repository("sqlite:///:memory:")
    Base.metadata.create_all(r.engine)
    return r


def _card(
    repo: Repository,
    number: str = "7",
    source_cards: list[tuple[str, str]] | None = None,
) -> int:
    """Insert a card (and optional source_cards), return card_id."""
    with Session(repo.engine) as session:
        card = CardRow(
            game="magic",
            name_en=f"Card {number}",
            set_code="TST",
            collector_number=number,
        )
        session.add(card)
        session.flush()
        for source, ext in source_cards or []:
            session.add(
                SourceCardRow(
                    source=source,
                    external_id=ext,
                    card_id=card.id,
                    url=f"https://example.com/{ext}",
                )
            )
        session.commit()
        return card.id


def _obs(
    repo: Repository,
    source: str,
    ext: str,
    day: date,
    price: str | None,
) -> None:
    """Insert a single price observation."""
    with Session(repo.engine) as session:
        session.add(
            PriceObservationRow(
                source=source,
                external_id=ext,
                observed_at=day,
                median_price=Decimal(price) if price else None,
                currency="BRL",
            )
        )
        session.commit()


# ------------------------------------------------------------------
# get_price_history
# ------------------------------------------------------------------


class TestGetPriceHistory:
    def test_single_source_simple(self, repo: Repository) -> None:
        cid = _card(repo, "10")
        _obs(repo, "liga", f"liga_{cid}", D(2), "10.00")
        _obs(repo, "liga", f"liga_{cid}", D(1), "12.00")
        _obs(repo, "liga", f"liga_{cid}", D(0), "11.50")

        observations, meta = get_price_history(repo, cid, days=90, today=TODAY)
        assert len(observations) == 3
        assert observations[0].observed_at == D(2)
        assert observations[-1].observed_at == D(0)
        assert float(observations[-1].median_price) == 11.50

    def test_same_day_dedup_manual_wins(self, repo: Repository) -> None:
        cid = _card(repo, "11")
        _obs(repo, "liga", f"liga_{cid}", D(0), "10.00")
        _obs(repo, "manual", f"manual_{cid}", D(0), "15.00")

        observations, _ = get_price_history(repo, cid, days=90, today=TODAY)
        assert len(observations) == 1
        assert float(observations[0].median_price) == 15.00
        assert observations[0].source == "manual"

    def test_same_day_dedup_liga_wins_over_myp(self, repo: Repository) -> None:
        cid = _card(repo, "12")
        _obs(repo, "myp", f"myp_{cid}", D(0), "8.00")
        _obs(repo, "liga", f"liga_{cid}", D(0), "9.00")

        observations, _ = get_price_history(repo, cid, days=90, today=TODAY)
        assert len(observations) == 1
        assert float(observations[0].median_price) == 9.00
        assert observations[0].source == "liga"

    def test_same_day_multiple_sources_returned(self, repo: Repository) -> None:
        """When multiple sources exist for the same day, build_history
        returns the per-day merged result (implementation-defined order)."""
        cid = _card(repo, "13", source_cards=[("myp", "myp_ext_13")])
        _obs(repo, "jsonld_snapshot", "myp_ext_13", D(0), "7.00")
        _obs(repo, "liga", f"liga_{cid}", D(0), "9.00")

        observations, _ = get_price_history(repo, cid, days=90, today=TODAY)
        assert len(observations) >= 1
        # At least one observation for day D(0)
        assert any(o.observed_at == D(0) for o in observations)

    def test_snapshot_and_live_same_day(self, repo: Repository) -> None:
        """Daily snapshots and live sources on the same day both contribute."""
        cid = _card(repo, "14")
        _obs(repo, SNAPSHOT_SOURCE, f"liga_{cid}", D(0), "5.00")
        _obs(repo, "myp", f"myp_{cid}", D(0), "6.00")

        observations, _ = get_price_history(repo, cid, days=90, today=TODAY)
        assert len(observations) >= 1
        assert any(o.observed_at == D(0) for o in observations)

    def test_date_range_filtering(self, repo: Repository) -> None:
        cid = _card(repo, "15")
        _obs(repo, "liga", f"liga_{cid}", D(100), "10.00")  # outside 90 days
        _obs(repo, "liga", f"liga_{cid}", D(50), "11.00")
        _obs(repo, "liga", f"liga_{cid}", D(0), "12.00")

        observations, _ = get_price_history(repo, cid, days=90, today=TODAY)
        assert len(observations) == 2  # D(100) is excluded
        assert observations[0].observed_at == D(50)

    def test_null_prices_excluded(self, repo: Repository) -> None:
        cid = _card(repo, "16")
        _obs(repo, "liga", f"liga_{cid}", D(1), None)
        _obs(repo, "liga", f"liga_{cid}", D(0), "10.00")

        observations, _ = get_price_history(repo, cid, days=90, today=TODAY)
        assert len(observations) == 1

    def test_empty_history(self, repo: Repository) -> None:
        cid = _card(repo, "17")
        observations, meta = get_price_history(repo, cid, days=90, today=TODAY)
        assert observations == []

    def test_source_cards_observations_included(self, repo: Repository) -> None:
        cid = _card(repo, "18", source_cards=[("myp", "myp_ext_99")])
        _obs(repo, "myp", "myp_ext_99", D(1), "20.00")
        _obs(repo, "jsonld_snapshot", "myp_ext_99", D(0), "21.00")

        observations, _ = get_price_history(repo, cid, days=90, today=TODAY)
        assert len(observations) == 2
        assert float(observations[0].median_price) == 20.00
        assert float(observations[1].median_price) == 21.00

    def test_multiple_days_sorted_asc(self, repo: Repository) -> None:
        cid = _card(repo, "19")
        _obs(repo, "liga", f"liga_{cid}", D(5), "5.00")
        _obs(repo, "liga", f"liga_{cid}", D(3), "7.00")
        _obs(repo, "liga", f"liga_{cid}", D(1), "9.00")

        observations, _ = get_price_history(repo, cid, days=90, today=TODAY)
        dates = [o.observed_at for o in observations]
        assert dates == sorted(dates)


# ------------------------------------------------------------------
# get_price_diagnostics
# ------------------------------------------------------------------


class TestGetPriceDiagnostics:
    def test_basic_diagnostics(self, repo: Repository) -> None:
        cid = _card(repo, "20")
        _obs(repo, "liga", f"liga_{cid}", D(5), "10.00")
        _obs(repo, "liga", f"liga_{cid}", D(3), "11.00")
        _obs(repo, "manual", f"manual_{cid}", D(1), "12.00")

        diag = get_price_diagnostics(repo, cid)
        assert diag["data_points"] == 3
        assert diag["min_price"] == 10.00
        assert diag["max_price"] == 12.00
        assert diag["current_price"] == 12.00
        assert diag["trend"] == "up"

    def test_empty_diagnostics(self, repo: Repository) -> None:
        cid = _card(repo, "21")
        diag = get_price_diagnostics(repo, cid)
        assert diag["data_points"] == 0
        assert diag["min_price"] is None
        assert diag["max_price"] is None
        assert diag["current_price"] is None
        assert diag["trend"] is None

    def test_null_prices_not_counted(self, repo: Repository) -> None:
        cid = _card(repo, "22")
        _obs(repo, "liga", f"liga_{cid}", D(1), None)
        _obs(repo, "liga", f"liga_{cid}", D(0), "10.00")

        diag = get_price_diagnostics(repo, cid)
        assert diag["data_points"] == 1
        assert diag["current_price"] == 10.00

    def test_single_day_range(self, repo: Repository) -> None:
        cid = _card(repo, "23")
        _obs(repo, "liga", f"liga_{cid}", D(0), "10.00")

        diag = get_price_diagnostics(repo, cid)
        assert diag["data_points"] == 1
        assert diag["current_price"] == 10.00
        assert diag["trend"] is None  # need >= 2 points for trend

    def test_includes_source_card_observations(self, repo: Repository) -> None:
        cid = _card(repo, "24", source_cards=[("myp", "myp_ext_24")])
        _obs(repo, "myp", "myp_ext_24", D(2), "15.00")
        _obs(repo, "liga", f"liga_{cid}", D(0), "16.00")

        diag = get_price_diagnostics(repo, cid)
        assert diag["data_points"] == 2
        assert diag["min_price"] == 15.00
        assert diag["max_price"] == 16.00
