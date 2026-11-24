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
    resolve_variant_ids,
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
# resolve_variant_ids
# ------------------------------------------------------------------


class TestResolveVariantIds:
    def test_basic_patterns(self, repo: Repository) -> None:
        cid = _card(repo, "1")
        ids = resolve_variant_ids(cid, repo)
        assert f"liga_{cid}" in ids
        assert f"liga_{cid}_foil" in ids
        assert f"manual_{cid}" in ids
        assert f"myp_{cid}" in ids
        assert f"myp_{cid}_foil" in ids

    def test_includes_source_cards(self, repo: Repository) -> None:
        cid = _card(repo, "2", source_cards=[("myp", "myp_ext_42")])
        ids = resolve_variant_ids(cid, repo)
        assert "myp_ext_42" in ids

    def test_no_duplicates(self, repo: Repository) -> None:
        cid = _card(repo, "3", source_cards=[("myp", f"myp_{1}")])
        # myp_{card_id} is already in the base list; source_card with
        # the same external_id should not add a duplicate.
        # Note: card_id from _card is auto-incremented, so myp_1 != myp_{cid}
        ids = resolve_variant_ids(cid, repo)
        assert len(ids) == len(set(ids)), "Duplicate external_ids found"

    def test_invalid_card_id_raises(self, repo: Repository) -> None:
        with pytest.raises(ValueError):
            resolve_variant_ids(-1, repo)
        with pytest.raises(ValueError):
            resolve_variant_ids(0, repo)


# ------------------------------------------------------------------
# get_price_history
# ------------------------------------------------------------------


class TestGetPriceHistory:
    def test_single_source_simple(self, repo: Repository) -> None:
        cid = _card(repo, "10")
        _obs(repo, "liga", f"liga_{cid}", D(2), "10.00")
        _obs(repo, "liga", f"liga_{cid}", D(1), "12.00")
        _obs(repo, "liga", f"liga_{cid}", D(0), "11.50")

        history = get_price_history(cid, repo, days=90, today=TODAY)
        assert len(history) == 3
        assert history[0]["date"] == D(2).isoformat()
        assert history[-1]["date"] == D(0).isoformat()
        assert history[-1]["price"] == 11.50

    def test_same_day_dedup_manual_wins(self, repo: Repository) -> None:
        cid = _card(repo, "11")
        _obs(repo, "liga", f"liga_{cid}", D(0), "10.00")
        _obs(repo, "manual", f"manual_{cid}", D(0), "15.00")

        history = get_price_history(cid, repo, days=90, today=TODAY)
        assert len(history) == 1
        assert history[0]["price"] == 15.00
        assert history[0]["source"] == "manual"

    def test_same_day_dedup_liga_wins_over_myp(self, repo: Repository) -> None:
        cid = _card(repo, "12")
        _obs(repo, "myp", f"myp_{cid}", D(0), "8.00")
        _obs(repo, "liga", f"liga_{cid}", D(0), "9.00")

        history = get_price_history(cid, repo, days=90, today=TODAY)
        assert len(history) == 1
        assert history[0]["price"] == 9.00
        assert history[0]["source"] == "liga"

    def test_same_day_dedup_liga_wins_over_jsonld(self, repo: Repository) -> None:
        cid = _card(repo, "13", source_cards=[("myp", "myp_ext_13")])
        _obs(repo, "jsonld_snapshot", "myp_ext_13", D(0), "7.00")
        _obs(repo, "liga", f"liga_{cid}", D(0), "9.00")

        history = get_price_history(cid, repo, days=90, today=TODAY)
        assert len(history) == 1
        assert history[0]["source"] == "liga"

    def test_daily_snapshot_lowest_priority(self, repo: Repository) -> None:
        cid = _card(repo, "14")
        _obs(repo, SNAPSHOT_SOURCE, f"liga_{cid}", D(0), "5.00")
        _obs(repo, "myp", f"myp_{cid}", D(0), "6.00")

        history = get_price_history(cid, repo, days=90, today=TODAY)
        assert len(history) == 1
        assert history[0]["source"] == "myp"

    def test_date_range_filtering(self, repo: Repository) -> None:
        cid = _card(repo, "15")
        _obs(repo, "liga", f"liga_{cid}", D(100), "10.00")  # outside 90 days
        _obs(repo, "liga", f"liga_{cid}", D(50), "11.00")
        _obs(repo, "liga", f"liga_{cid}", D(0), "12.00")

        history = get_price_history(cid, repo, days=90, today=TODAY)
        assert len(history) == 2  # D(100) is excluded
        assert history[0]["date"] == D(50).isoformat()

    def test_null_prices_excluded(self, repo: Repository) -> None:
        cid = _card(repo, "16")
        _obs(repo, "liga", f"liga_{cid}", D(1), None)
        _obs(repo, "liga", f"liga_{cid}", D(0), "10.00")

        history = get_price_history(cid, repo, days=90, today=TODAY)
        assert len(history) == 1

    def test_empty_history(self, repo: Repository) -> None:
        cid = _card(repo, "17")
        history = get_price_history(cid, repo, days=90, today=TODAY)
        assert history == []

    def test_source_cards_observations_included(self, repo: Repository) -> None:
        cid = _card(repo, "18", source_cards=[("myp", "myp_ext_99")])
        _obs(repo, "myp", "myp_ext_99", D(1), "20.00")
        _obs(repo, "jsonld_snapshot", "myp_ext_99", D(0), "21.00")

        history = get_price_history(cid, repo, days=90, today=TODAY)
        assert len(history) == 2
        assert history[0]["price"] == 20.00
        assert history[1]["price"] == 21.00

    def test_multiple_days_sorted_asc(self, repo: Repository) -> None:
        cid = _card(repo, "19")
        _obs(repo, "liga", f"liga_{cid}", D(5), "5.00")
        _obs(repo, "liga", f"liga_{cid}", D(3), "7.00")
        _obs(repo, "liga", f"liga_{cid}", D(1), "9.00")

        history = get_price_history(cid, repo, days=90, today=TODAY)
        dates = [h["date"] for h in history]
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

        diag = get_price_diagnostics(cid, repo)
        assert diag["total_observations"] == 3
        assert diag["by_source"]["liga"] == 2
        assert diag["by_source"]["manual"] == 1
        assert diag["first_seen"] == D(5).isoformat()
        assert diag["last_seen"] == D(1).isoformat()
        assert diag["days_with_data"] == 3
        assert diag["total_days_in_range"] == 5  # D(5) to D(1) inclusive

    def test_empty_diagnostics(self, repo: Repository) -> None:
        cid = _card(repo, "21")
        diag = get_price_diagnostics(cid, repo)
        assert diag["total_observations"] == 0
        assert diag["by_source"] == {}
        assert diag["first_seen"] is None
        assert diag["last_seen"] is None
        assert diag["days_with_data"] == 0
        assert diag["total_days_in_range"] == 0

    def test_null_prices_not_counted(self, repo: Repository) -> None:
        cid = _card(repo, "22")
        _obs(repo, "liga", f"liga_{cid}", D(1), None)
        _obs(repo, "liga", f"liga_{cid}", D(0), "10.00")

        diag = get_price_diagnostics(cid, repo)
        assert diag["total_observations"] == 1
        assert diag["days_with_data"] == 1

    def test_single_day_range(self, repo: Repository) -> None:
        cid = _card(repo, "23")
        _obs(repo, "liga", f"liga_{cid}", D(0), "10.00")

        diag = get_price_diagnostics(cid, repo)
        assert diag["total_days_in_range"] == 1
        assert diag["days_with_data"] == 1

    def test_includes_source_card_observations(self, repo: Repository) -> None:
        cid = _card(repo, "24", source_cards=[("myp", "myp_ext_24")])
        _obs(repo, "myp", "myp_ext_24", D(2), "15.00")
        _obs(repo, "liga", f"liga_{cid}", D(0), "16.00")

        diag = get_price_diagnostics(cid, repo)
        assert diag["total_observations"] == 2
        assert "myp" in diag["by_source"]
        assert "liga" in diag["by_source"]
