"""Gap tests for F112 Portfolio History Backfill — QA agent.

Covers edge cases identified during QA review:
- Nonexistent user returns clean result
- Collection with only foil source_card entries
- Multiple source_cards per card (foil + non-foil)
- _find_best_price with unknown external_id in list
- backfill_acquisition_prices with empty price_observations table
- backfill_portfolio_snapshots with days=0 (today only)
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from src.collectors.portfolio_backfill import (
    _find_best_price,
    _find_nearest_observation,
    backfill_acquisition_prices,
    backfill_portfolio_snapshots,
)
from src.database.models import (
    Base,
    CardRow,
    PriceObservationRow,
    SourceCardRow,
    UserCollectionRow,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_engine():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _pragma(dbapi_conn, _rec):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


def _seed_card(session, card_id=1, name="Test Card"):
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


def _seed_source_card(session, card_id, source="liga", external_id="liga_100"):
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


def _seed_observation(session, source, external_id, observed_at, **prices):
    obs = PriceObservationRow(
        source=source,
        external_id=external_id,
        observed_at=observed_at,
        median_price=prices.get("median_price"),
        tcg_price=prices.get("tcg_price"),
        last_sold_price=prices.get("last_sold_price"),
        created_at=datetime(2026, 1, 1),
    )
    session.add(obs)
    session.flush()
    return obs


def _seed_collection_entry(session, user_id, card_id, created_at, **kwargs):
    entry = UserCollectionRow(
        user_id=user_id,
        card_id=card_id,
        set_code="TST",
        collector_number="001",
        name_en="Test Card",
        quantity=kwargs.get("quantity", 1),
        acquisition_price=kwargs.get("acquisition_price"),
        acquired_at=kwargs.get("acquired_at"),
        created_at=created_at,
    )
    session.add(entry)
    session.flush()
    return entry


class FakeRepo:
    def __init__(self, engine):
        self.engine = engine


# ---------------------------------------------------------------------------
# Gap: nonexistent user
# ---------------------------------------------------------------------------


class TestNonexistentUser:
    def test_backfill_prices_nonexistent_user_returns_zero(self):
        """Calling backfill for a user with no collection entries returns zero."""
        engine = _make_engine()
        repo = FakeRepo(engine)

        result = backfill_acquisition_prices(repo, user_id="nonexistent-user")
        assert result == {"updated": 0, "skipped": 0, "total": 0}

    @patch("src.collectors.portfolio_backfill.Session")
    def test_backfill_snapshots_nonexistent_user_returns_zero(self, mock_session_cls):
        """Calling snapshot backfill for user with no collection returns zero."""
        # Mock session returning empty collection
        session = MagicMock()
        snap_scalars = MagicMock()
        snap_scalars.all.return_value = []
        snap_result = MagicMock()
        snap_result.scalars.return_value = snap_scalars

        coll_scalars = MagicMock()
        coll_scalars.all.return_value = []
        coll_result = MagicMock()
        coll_result.scalars.return_value = coll_scalars

        session.execute = MagicMock(side_effect=[snap_result, coll_result])

        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=session)
        ctx.__exit__ = MagicMock(return_value=False)
        mock_session_cls.return_value = ctx

        repo = MagicMock()
        repo.engine = MagicMock()

        result = backfill_portfolio_snapshots(repo, "ghost-user", days=7)
        assert result == {"days_filled": 0, "days_skipped": 0}
        repo.upsert_portfolio_snapshot.assert_not_called()


# ---------------------------------------------------------------------------
# Gap: foil-only collection
# ---------------------------------------------------------------------------


class TestFoilEntries:
    def test_backfill_with_foil_source_card(self):
        """Foil entries (external_id ending with _foil) are correctly handled."""
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            # Only a foil source_card
            _seed_source_card(
                session,
                card_id=1,
                source="liga",
                external_id="liga_100_foil",
            )
            _seed_observation(
                session,
                source="liga",
                external_id="liga_100_foil",
                observed_at=date(2026, 8, 15),
                median_price=Decimal("25.00"),
            )
            _seed_collection_entry(
                session,
                user_id="user1",
                card_id=1,
                created_at=datetime(2026, 8, 15),
            )
            session.commit()

        repo = FakeRepo(engine)
        result = backfill_acquisition_prices(repo)

        assert result == {"updated": 1, "skipped": 0, "total": 1}

        with Session(engine) as session:
            entry = session.get(UserCollectionRow, 1)
            assert entry.acquisition_price == Decimal("25.00")

    def test_backfill_prefers_closer_observation_across_foil_and_regular(self):
        """When both foil and regular source_cards exist, picks closest observation."""
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            _seed_source_card(session, card_id=1, source="liga", external_id="liga_100")
            _seed_source_card(session, card_id=1, source="liga", external_id="liga_100_foil")
            # Regular: observation 5 days before target
            _seed_observation(
                session,
                source="liga",
                external_id="liga_100",
                observed_at=date(2026, 8, 10),
                median_price=Decimal("10.00"),
            )
            # Foil: observation 1 day before target (closer)
            _seed_observation(
                session,
                source="liga",
                external_id="liga_100_foil",
                observed_at=date(2026, 8, 14),
                median_price=Decimal("50.00"),
            )
            _seed_collection_entry(
                session,
                user_id="user1",
                card_id=1,
                created_at=datetime(2026, 8, 15),
            )
            session.commit()

        repo = FakeRepo(engine)
        result = backfill_acquisition_prices(repo)

        assert result["updated"] == 1

        with Session(engine) as session:
            entry = session.get(UserCollectionRow, 1)
            # The foil observation (Aug 14) is closer to target (Aug 15)
            assert entry.acquisition_price == Decimal("50.00")


# ---------------------------------------------------------------------------
# Gap: _find_best_price edge cases
# ---------------------------------------------------------------------------


class TestFindBestPriceEdgeCases:
    def test_unknown_external_id_in_list(self):
        """Unknown external_ids in the list are safely ignored."""
        price_index = {
            "ext_1": (
                [date(2026, 8, 1)],
                [Decimal("10.00")],
            ),
        }
        # "ext_unknown" is not in the index — should still find ext_1
        result = _find_best_price(
            price_index,
            ["ext_unknown", "ext_1"],
            date(2026, 8, 5),
        )
        assert result == Decimal("10.00")

    def test_all_external_ids_unknown(self):
        """When all external_ids are unknown, returns None."""
        price_index = {
            "ext_1": (
                [date(2026, 8, 1)],
                [Decimal("10.00")],
            ),
        }
        result = _find_best_price(
            price_index,
            ["ext_unknown_a", "ext_unknown_b"],
            date(2026, 8, 5),
        )
        assert result is None

    def test_empty_price_index(self):
        """Empty price index returns None regardless of external_ids."""
        result = _find_best_price({}, ["ext_1", "ext_2"], date(2026, 8, 5))
        assert result is None


# ---------------------------------------------------------------------------
# Gap: all cards missing source_cards link
# ---------------------------------------------------------------------------


class TestAllCardsUnlinked:
    def test_backfill_prices_all_entries_no_source_cards(self):
        """All collection entries have card_id but no source_cards -- all skipped."""
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            _seed_card(session, card_id=2, name="Card 2")
            # No source_cards seeded
            _seed_collection_entry(
                session,
                user_id="user1",
                card_id=1,
                created_at=datetime(2026, 8, 15),
            )
            _seed_collection_entry(
                session,
                user_id="user1",
                card_id=2,
                created_at=datetime(2026, 8, 15),
            )
            session.commit()

        repo = FakeRepo(engine)
        result = backfill_acquisition_prices(repo)

        # Both have card_id but no source_cards -> no observations found
        assert result == {"updated": 0, "skipped": 2, "total": 2}


# ---------------------------------------------------------------------------
# Gap: empty price_observations table
# ---------------------------------------------------------------------------


class TestEmptyPriceObservations:
    def test_backfill_prices_no_observations_anywhere(self):
        """When price_observations table is completely empty, all entries skip."""
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            _seed_source_card(session, card_id=1, source="liga", external_id="liga_1")
            _seed_collection_entry(
                session,
                user_id="user1",
                card_id=1,
                created_at=datetime(2026, 8, 15),
            )
            session.commit()

        repo = FakeRepo(engine)
        result = backfill_acquisition_prices(repo)

        assert result == {"updated": 0, "skipped": 1, "total": 1}

    def test_find_nearest_observation_returns_none_empty_table(self):
        """_find_nearest_observation returns None when observations table is empty."""
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            _seed_source_card(session, card_id=1, source="liga", external_id="liga_1")
            session.commit()

        with Session(engine) as session:
            obs = _find_nearest_observation(session, card_id=1, target_dt=datetime(2026, 8, 15))
            assert obs is None


# ---------------------------------------------------------------------------
# Gap: backfill_portfolio_snapshots with days=0 (today only)
# ---------------------------------------------------------------------------


class TestSnapshotDaysZero:
    @patch("src.collectors.portfolio_backfill.Session")
    def test_days_zero_fills_today_only(self, mock_session_cls):
        """days=0 should create exactly 1 snapshot for today."""
        entry = MagicMock()
        entry.card_id = 1
        entry.quantity = 1
        entry.created_at = datetime(2026, 8, 1)

        session = MagicMock()
        snap_scalars = MagicMock()
        snap_scalars.all.return_value = []
        snap_result = MagicMock()
        snap_result.scalars.return_value = snap_scalars

        coll_scalars = MagicMock()
        coll_scalars.all.return_value = [entry]
        coll_result = MagicMock()
        coll_result.scalars.return_value = coll_scalars

        src_result = MagicMock()
        src_result.all.return_value = [(1, "ext_1")]

        price_result = MagicMock()
        price_result.all.return_value = [
            ("ext_1", date.today(), Decimal("10.00"), None, None),
        ]

        session.execute = MagicMock(
            side_effect=[snap_result, coll_result, src_result, price_result]
        )

        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=session)
        ctx.__exit__ = MagicMock(return_value=False)
        mock_session_cls.return_value = ctx

        repo = MagicMock()
        repo.engine = MagicMock()

        result = backfill_portfolio_snapshots(repo, "user1", days=0)

        assert result["days_filled"] == 1
        assert result["days_skipped"] == 0
        repo.upsert_portfolio_snapshot.assert_called_once()
        call_kwargs = repo.upsert_portfolio_snapshot.call_args.kwargs
        assert call_kwargs["snapshot_date"] == date.today()


# ---------------------------------------------------------------------------
# Gap: quantity multiplier in backfill
# ---------------------------------------------------------------------------


class TestQuantityMultiplier:
    def test_backfill_acquisition_price_ignores_quantity(self):
        """Acquisition price is per-card, not multiplied by quantity."""
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            _seed_source_card(session, card_id=1, source="liga", external_id="liga_1")
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
                quantity=4,
            )
            session.commit()

        repo = FakeRepo(engine)
        backfill_acquisition_prices(repo)

        with Session(engine) as session:
            entry = session.get(UserCollectionRow, 1)
            # Price should be per-card, not 10.00 * 4
            assert entry.acquisition_price == Decimal("10.00")
