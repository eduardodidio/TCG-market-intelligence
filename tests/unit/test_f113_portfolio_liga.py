"""Tests for F113-T07: Portfolio/Liga Dashboard Data Flow Fix.

Covers:
- Bug A: _load_card_external_ids includes foil Liga patterns
- Bug A: _find_nearest_observation includes foil Liga patterns
- Bug B: get_collection_summary priced_count includes Liga-only cards
- Bug D: get_trending_price_data_for_user includes Liga direct patterns
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from src.collectors.portfolio_backfill import (
    _find_nearest_observation,
    _load_card_external_ids,
)
from src.database.models import (
    Base,
    CardRow,
    PriceObservationRow,
    SourceCardRow,
    UserCollectionRow,
)
from src.database.repository import Repository

# ── Helpers ──────────────────────────────────────────────────────


def _make_engine():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _pragma(dbapi_conn, _rec):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


def _seed_card(session: Session, card_id: int = 1, name: str = "Test Card") -> CardRow:
    card = CardRow(
        id=card_id,
        game="magic",
        name_en=name,
        set_code="TST",
        collector_number=str(card_id).zfill(3),
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
    )
    session.add(card)
    session.flush()
    return card


def _seed_source_card(
    session: Session,
    card_id: int,
    source: str = "liga",
    external_id: str = "liga_100",
) -> SourceCardRow:
    sc = SourceCardRow(
        source=source,
        external_id=external_id,
        card_id=card_id,
        url=f"https://example.com/{external_id}",
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
    )
    session.add(sc)
    session.flush()
    return sc


def _seed_observation(
    session: Session,
    source: str,
    external_id: str,
    observed_at: date,
    median_price: Decimal | None = None,
    tcg_price: Decimal | None = None,
    last_sold_price: Decimal | None = None,
) -> PriceObservationRow:
    obs = PriceObservationRow(
        source=source,
        external_id=external_id,
        observed_at=observed_at,
        median_price=median_price,
        tcg_price=tcg_price,
        last_sold_price=last_sold_price,
        created_at=datetime(2026, 1, 1),
    )
    session.add(obs)
    session.flush()
    return obs


def _seed_collection_entry(
    session: Session,
    user_id: str,
    card_id: int | None,
    created_at: datetime,
    extras: str | None = None,
    quantity: int = 1,
) -> UserCollectionRow:
    entry = UserCollectionRow(
        user_id=user_id,
        card_id=card_id,
        set_code="TST",
        collector_number="001",
        name_en="Test Card",
        quantity=quantity,
        extras=extras,
        created_at=created_at,
    )
    session.add(entry)
    session.flush()
    return entry


# ── Bug A: _load_card_external_ids with foil support ─────────────


class TestLoadCardExternalIdsFoil:
    """Verify that _load_card_external_ids includes foil Liga patterns."""

    def test_no_foil_ids_only_liga_and_manual(self):
        """Without foil_card_ids, only liga_{id} and manual_{id} are added."""
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            session.commit()

        with Session(engine) as session:
            result = _load_card_external_ids(session, {1})
            ext_ids = result[1]
            assert "liga_1" in ext_ids
            assert "manual_1" in ext_ids
            assert "liga_1_foil" not in ext_ids

    def test_foil_card_gets_foil_pattern(self):
        """When card_id is in foil_card_ids, liga_{id}_foil is added."""
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            session.commit()

        with Session(engine) as session:
            result = _load_card_external_ids(session, {1}, foil_card_ids={1})
            ext_ids = result[1]
            assert "liga_1_foil" in ext_ids
            assert "liga_1" in ext_ids
            assert "manual_1" in ext_ids

    def test_foil_pattern_appears_first(self):
        """Foil pattern should be inserted at position 0 for priority."""
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=5)
            session.commit()

        with Session(engine) as session:
            result = _load_card_external_ids(session, {5}, foil_card_ids={5})
            ext_ids = result[5]
            assert ext_ids[0] == "liga_5_foil"

    def test_mixed_foil_and_non_foil(self):
        """Only foil card_ids get the foil pattern."""
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            _seed_card(session, card_id=2, name="Card 2")
            session.commit()

        with Session(engine) as session:
            result = _load_card_external_ids(session, {1, 2}, foil_card_ids={2})
            assert "liga_1_foil" not in result[1]
            assert "liga_2_foil" in result[2]


# ── Bug A: _find_nearest_observation with foil support ───────────


class TestFindNearestObservationFoil:
    """Verify that _find_nearest_observation searches foil patterns."""

    def test_finds_foil_observation(self):
        """When is_foil=True, finds liga_{id}_foil observations."""
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            _seed_observation(
                session,
                source="liga",
                external_id="liga_1_foil",
                observed_at=date(2026, 8, 15),
                median_price=Decimal("25.00"),
            )
            session.commit()

        with Session(engine) as session:
            obs = _find_nearest_observation(
                session, card_id=1, target_dt=datetime(2026, 8, 15), is_foil=True
            )
            assert obs is not None
            assert obs.external_id == "liga_1_foil"
            assert obs.median_price == Decimal("25.00")

    def test_foil_not_found_without_flag(self):
        """When is_foil=False, does not search liga_{id}_foil."""
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            # Only a foil observation exists
            _seed_observation(
                session,
                source="liga",
                external_id="liga_1_foil",
                observed_at=date(2026, 8, 15),
                median_price=Decimal("25.00"),
            )
            session.commit()

        with Session(engine) as session:
            obs = _find_nearest_observation(
                session, card_id=1, target_dt=datetime(2026, 8, 15), is_foil=False
            )
            # Should NOT find the foil observation
            assert obs is None

    def test_foil_preferred_over_normal_when_closer(self):
        """When both foil and normal observations exist, the closer one wins."""
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            # Normal Liga price from Aug 10
            _seed_observation(
                session,
                source="liga",
                external_id="liga_1",
                observed_at=date(2026, 8, 10),
                median_price=Decimal("10.00"),
            )
            # Foil Liga price from Aug 14 (closer to target)
            _seed_observation(
                session,
                source="liga",
                external_id="liga_1_foil",
                observed_at=date(2026, 8, 14),
                median_price=Decimal("30.00"),
            )
            session.commit()

        with Session(engine) as session:
            obs = _find_nearest_observation(
                session, card_id=1, target_dt=datetime(2026, 8, 15), is_foil=True
            )
            assert obs is not None
            assert obs.external_id == "liga_1_foil"
            assert obs.median_price == Decimal("30.00")


# ── Bug B: get_collection_summary priced_count ───────────────────


class TestCollectionSummaryPricedCount:
    """Verify priced_count includes Liga-only cards (no source_cards entry)."""

    def test_liga_only_card_counted_as_priced(self):
        """A card with only a liga_{id} price observation should be counted as priced."""
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            # No source_card entry — only a direct Liga observation
            _seed_observation(
                session,
                source="liga",
                external_id="liga_1",
                observed_at=date(2026, 8, 15),
                median_price=Decimal("10.00"),
            )
            _seed_collection_entry(
                session,
                user_id="user1",
                card_id=1,
                created_at=datetime(2026, 8, 15),
            )
            session.commit()

        repo = Repository.__new__(Repository)
        repo.engine = engine

        summary = repo.get_collection_summary("user1")
        assert summary["priced_count"] == 1

    def test_liga_foil_card_counted_as_priced(self):
        """A card with only a liga_{id}_foil price observation should be counted as priced."""
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            _seed_observation(
                session,
                source="liga",
                external_id="liga_1_foil",
                observed_at=date(2026, 8, 15),
                median_price=Decimal("25.00"),
            )
            _seed_collection_entry(
                session,
                user_id="user1",
                card_id=1,
                created_at=datetime(2026, 8, 15),
                extras="Foil",
            )
            session.commit()

        repo = Repository.__new__(Repository)
        repo.engine = engine

        summary = repo.get_collection_summary("user1")
        assert summary["priced_count"] == 1

    def test_source_card_priced_still_works(self):
        """Cards priced via source_cards should still be counted."""
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            _seed_source_card(session, card_id=1, source="myp", external_id="myp_100")
            _seed_observation(
                session,
                source="myp",
                external_id="myp_100",
                observed_at=date(2026, 8, 15),
                median_price=Decimal("5.00"),
            )
            _seed_collection_entry(
                session,
                user_id="user1",
                card_id=1,
                created_at=datetime(2026, 8, 15),
            )
            session.commit()

        repo = Repository.__new__(Repository)
        repo.engine = engine

        summary = repo.get_collection_summary("user1")
        assert summary["priced_count"] == 1

    def test_manual_price_counted(self):
        """A card with only a manual_{id} price should be counted as priced."""
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            _seed_observation(
                session,
                source="manual",
                external_id="manual_1",
                observed_at=date(2026, 8, 15),
                median_price=Decimal("15.00"),
            )
            _seed_collection_entry(
                session,
                user_id="user1",
                card_id=1,
                created_at=datetime(2026, 8, 15),
            )
            session.commit()

        repo = Repository.__new__(Repository)
        repo.engine = engine

        summary = repo.get_collection_summary("user1")
        assert summary["priced_count"] == 1


# ── Bug D: get_trending_price_data_for_user includes Liga ────────


class TestTrendingPriceDataLiga:
    """Verify movers endpoint data includes Liga direct patterns."""

    def test_liga_only_card_appears_in_trending(self):
        """A card with only Liga direct prices should appear in trending data."""
        engine = _make_engine()
        today = date.today()
        yesterday = today - timedelta(days=1)

        with Session(engine) as session:
            _seed_card(session, card_id=1)
            # No source_card entry — only direct Liga observations
            _seed_observation(
                session,
                source="liga",
                external_id="liga_1",
                observed_at=yesterday,
                median_price=Decimal("10.00"),
            )
            _seed_observation(
                session,
                source="liga",
                external_id="liga_1",
                observed_at=today,
                median_price=Decimal("12.00"),
            )
            _seed_collection_entry(
                session,
                user_id="user1",
                card_id=1,
                created_at=datetime(2026, 8, 1),
            )
            session.commit()

        repo = Repository.__new__(Repository)
        repo.engine = engine

        result = repo.get_trending_price_data_for_user("user1", period_days=7)
        assert 1 in result
        assert len(result[1]) >= 2
        # Check prices are present
        prices = {p for _, p in result[1]}
        assert Decimal("10.00") in prices
        assert Decimal("12.00") in prices

    def test_liga_foil_card_appears_in_trending(self):
        """A foil card with liga_{id}_foil prices should appear in trending data."""
        engine = _make_engine()
        today = date.today()
        yesterday = today - timedelta(days=1)

        with Session(engine) as session:
            _seed_card(session, card_id=2, name="Foil Card")
            _seed_observation(
                session,
                source="liga",
                external_id="liga_2_foil",
                observed_at=yesterday,
                median_price=Decimal("20.00"),
            )
            _seed_observation(
                session,
                source="liga",
                external_id="liga_2_foil",
                observed_at=today,
                median_price=Decimal("25.00"),
            )
            _seed_collection_entry(
                session,
                user_id="user1",
                card_id=2,
                created_at=datetime(2026, 8, 1),
                extras="Foil",
            )
            session.commit()

        repo = Repository.__new__(Repository)
        repo.engine = engine

        result = repo.get_trending_price_data_for_user("user1", period_days=7)
        assert 2 in result
        assert len(result[2]) >= 2

    def test_source_card_prices_still_work(self):
        """Cards priced via source_cards should still appear in trending data."""
        engine = _make_engine()
        today = date.today()
        yesterday = today - timedelta(days=1)

        with Session(engine) as session:
            _seed_card(session, card_id=1)
            _seed_source_card(session, card_id=1, source="myp", external_id="myp_100")
            _seed_observation(
                session,
                source="myp",
                external_id="myp_100",
                observed_at=yesterday,
                median_price=Decimal("5.00"),
            )
            _seed_observation(
                session,
                source="myp",
                external_id="myp_100",
                observed_at=today,
                median_price=Decimal("6.00"),
            )
            _seed_collection_entry(
                session,
                user_id="user1",
                card_id=1,
                created_at=datetime(2026, 8, 1),
            )
            session.commit()

        repo = Repository.__new__(Repository)
        repo.engine = engine

        result = repo.get_trending_price_data_for_user("user1", period_days=7)
        assert 1 in result
        assert len(result[1]) >= 2
