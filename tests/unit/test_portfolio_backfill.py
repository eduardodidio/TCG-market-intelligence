"""Tests for portfolio_backfill — backfill acquisition prices from price history."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from src.collectors.portfolio_backfill import (
    _find_nearest_observation,
    _pick_price,
    backfill_acquisition_prices,
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
    acquisition_price: Decimal | None = None,
    acquired_at: date | None = None,
) -> UserCollectionRow:
    entry = UserCollectionRow(
        user_id=user_id,
        card_id=card_id,
        set_code="TST",
        collector_number="001",
        name_en="Test Card",
        quantity=1,
        acquisition_price=acquisition_price,
        acquired_at=acquired_at,
        created_at=created_at,
    )
    session.add(entry)
    session.flush()
    return entry


class FakeRepo:
    """Minimal repo-like object exposing engine for backfill."""

    def __init__(self, engine):
        self.engine = engine


# ---------------------------------------------------------------------------
# _pick_price unit tests
# ---------------------------------------------------------------------------


class TestPickPrice:
    def test_prefers_median_price(self):
        obs = PriceObservationRow(
            source="liga",
            external_id="x",
            observed_at=date(2026, 1, 1),
            median_price=Decimal("10.00"),
            tcg_price=Decimal("12.00"),
            last_sold_price=Decimal("8.00"),
        )
        assert _pick_price(obs) == Decimal("10.00")

    def test_falls_back_to_tcg_price(self):
        obs = PriceObservationRow(
            source="liga",
            external_id="x",
            observed_at=date(2026, 1, 1),
            median_price=None,
            tcg_price=Decimal("12.00"),
            last_sold_price=Decimal("8.00"),
        )
        assert _pick_price(obs) == Decimal("12.00")

    def test_falls_back_to_last_sold_price(self):
        obs = PriceObservationRow(
            source="liga",
            external_id="x",
            observed_at=date(2026, 1, 1),
            median_price=None,
            tcg_price=None,
            last_sold_price=Decimal("8.00"),
        )
        assert _pick_price(obs) == Decimal("8.00")

    def test_returns_none_when_all_null(self):
        obs = PriceObservationRow(
            source="liga",
            external_id="x",
            observed_at=date(2026, 1, 1),
            median_price=None,
            tcg_price=None,
            last_sold_price=None,
        )
        assert _pick_price(obs) is None


# ---------------------------------------------------------------------------
# _find_nearest_observation unit tests
# ---------------------------------------------------------------------------


class TestFindNearestObservation:
    def test_finds_observation_on_same_date(self):
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            _seed_source_card(session, card_id=1, source="liga", external_id="liga_1")
            _seed_observation(
                session,
                source="liga",
                external_id="liga_1",
                observed_at=date(2026, 8, 15),
                median_price=Decimal("5.00"),
            )
            session.commit()

        with Session(engine) as session:
            obs = _find_nearest_observation(session, card_id=1, target_dt=datetime(2026, 8, 15))
            assert obs is not None
            assert obs.observed_at == date(2026, 8, 15)

    def test_prefers_observation_before_target(self):
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            _seed_source_card(session, card_id=1, source="liga", external_id="liga_1")
            _seed_observation(
                session,
                source="liga",
                external_id="liga_1",
                observed_at=date(2026, 8, 10),
                median_price=Decimal("4.00"),
            )
            _seed_observation(
                session,
                source="liga",
                external_id="liga_1",
                observed_at=date(2026, 8, 20),
                median_price=Decimal("6.00"),
            )
            session.commit()

        with Session(engine) as session:
            obs = _find_nearest_observation(session, card_id=1, target_dt=datetime(2026, 8, 14))
            assert obs is not None
            # Should pick Aug 10 (before target), not Aug 20 (after)
            assert obs.observed_at == date(2026, 8, 10)

    def test_falls_back_to_after_when_none_before(self):
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            _seed_source_card(session, card_id=1, source="liga", external_id="liga_1")
            _seed_observation(
                session,
                source="liga",
                external_id="liga_1",
                observed_at=date(2026, 8, 20),
                median_price=Decimal("6.00"),
            )
            session.commit()

        with Session(engine) as session:
            obs = _find_nearest_observation(session, card_id=1, target_dt=datetime(2026, 8, 10))
            assert obs is not None
            assert obs.observed_at == date(2026, 8, 20)

    def test_returns_none_when_no_source_cards(self):
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            session.commit()

        with Session(engine) as session:
            obs = _find_nearest_observation(session, card_id=1, target_dt=datetime(2026, 8, 10))
            assert obs is None

    def test_returns_none_when_no_observations(self):
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            _seed_source_card(session, card_id=1, source="liga", external_id="liga_1")
            session.commit()

        with Session(engine) as session:
            obs = _find_nearest_observation(session, card_id=1, target_dt=datetime(2026, 8, 10))
            assert obs is None


# ---------------------------------------------------------------------------
# backfill_acquisition_prices integration tests
# ---------------------------------------------------------------------------


class TestBackfillAcquisitionPrices:
    def test_updates_null_entries(self):
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            _seed_source_card(session, card_id=1, source="liga", external_id="liga_1")
            _seed_observation(
                session,
                source="liga",
                external_id="liga_1",
                observed_at=date(2026, 8, 15),
                median_price=Decimal("10.50"),
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
            assert entry.acquisition_price == Decimal("10.50")
            assert entry.acquired_at == date(2026, 8, 15)

    def test_does_not_overwrite_existing_price(self):
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            _seed_source_card(session, card_id=1, source="liga", external_id="liga_1")
            _seed_observation(
                session,
                source="liga",
                external_id="liga_1",
                observed_at=date(2026, 8, 15),
                median_price=Decimal("10.50"),
            )
            # Entry already has an acquisition_price
            _seed_collection_entry(
                session,
                user_id="user1",
                card_id=1,
                created_at=datetime(2026, 8, 15),
                acquisition_price=Decimal("5.00"),
                acquired_at=date(2026, 8, 10),
            )
            session.commit()

        repo = FakeRepo(engine)
        result = backfill_acquisition_prices(repo)

        # Entry had a price so it was not selected (acquisition_price IS NULL filter)
        assert result == {"updated": 0, "skipped": 0, "total": 0}

        with Session(engine) as session:
            entry = session.get(UserCollectionRow, 1)
            assert entry.acquisition_price == Decimal("5.00")
            assert entry.acquired_at == date(2026, 8, 10)

    def test_skips_entry_without_card_id(self):
        engine = _make_engine()
        with Session(engine) as session:
            _seed_collection_entry(
                session,
                user_id="user1",
                card_id=None,
                created_at=datetime(2026, 8, 15),
            )
            session.commit()

        repo = FakeRepo(engine)
        result = backfill_acquisition_prices(repo)

        assert result == {"updated": 0, "skipped": 1, "total": 1}

    def test_skips_entry_without_price_observations(self):
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

    def test_nearest_date_selection(self):
        """Picks the observation closest to created_at."""
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            _seed_source_card(session, card_id=1, source="liga", external_id="liga_1")
            # Observation 5 days before
            _seed_observation(
                session,
                source="liga",
                external_id="liga_1",
                observed_at=date(2026, 8, 10),
                median_price=Decimal("8.00"),
            )
            # Observation 1 day before (closer)
            _seed_observation(
                session,
                source="liga",
                external_id="liga_1",
                observed_at=date(2026, 8, 14),
                median_price=Decimal("9.50"),
            )
            # Observation 3 days after
            _seed_observation(
                session,
                source="liga",
                external_id="liga_1",
                observed_at=date(2026, 8, 18),
                median_price=Decimal("11.00"),
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
            # Aug 14 is closest before target (1 day), Aug 18 is 3 days after
            assert entry.acquisition_price == Decimal("9.50")
            assert entry.acquired_at == date(2026, 8, 14)

    def test_user_id_filter(self):
        """Only backfills entries for the given user_id."""
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
            )
            _seed_card(session, card_id=2, name="Card 2")
            _seed_source_card(session, card_id=2, source="liga", external_id="liga_2")
            _seed_observation(
                session,
                source="liga",
                external_id="liga_2",
                observed_at=date(2026, 8, 15),
                median_price=Decimal("20.00"),
            )
            _seed_collection_entry(
                session,
                user_id="user2",
                card_id=2,
                created_at=datetime(2026, 8, 15),
            )
            session.commit()

        repo = FakeRepo(engine)
        result = backfill_acquisition_prices(repo, user_id="user1")

        assert result == {"updated": 1, "skipped": 0, "total": 1}

        with Session(engine) as session:
            entries = session.query(UserCollectionRow).all()
            user1_entry = [e for e in entries if e.user_id == "user1"][0]
            user2_entry = [e for e in entries if e.user_id == "user2"][0]
            assert user1_entry.acquisition_price == Decimal("10.00")
            # user2 should remain untouched
            assert user2_entry.acquisition_price is None

    def test_idempotent(self):
        """Running backfill twice produces the same result."""
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
            )
            session.commit()

        repo = FakeRepo(engine)

        result1 = backfill_acquisition_prices(repo)
        assert result1["updated"] == 1

        result2 = backfill_acquisition_prices(repo)
        assert result2["updated"] == 0
        assert result2["total"] == 0  # no NULL entries left

        # Price should still be the original
        with Session(engine) as session:
            entry = session.get(UserCollectionRow, 1)
            assert entry.acquisition_price == Decimal("10.00")

    def test_price_fallback_tcg(self):
        """Uses tcg_price when median_price is None."""
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            _seed_source_card(session, card_id=1, source="liga", external_id="liga_1")
            _seed_observation(
                session,
                source="liga",
                external_id="liga_1",
                observed_at=date(2026, 8, 15),
                median_price=None,
                tcg_price=Decimal("7.25"),
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
            assert entry.acquisition_price == Decimal("7.25")

    def test_skips_observation_with_all_prices_null(self):
        """Skips when the nearest observation has all price fields NULL."""
        engine = _make_engine()
        with Session(engine) as session:
            _seed_card(session, card_id=1)
            _seed_source_card(session, card_id=1, source="liga", external_id="liga_1")
            _seed_observation(
                session,
                source="liga",
                external_id="liga_1",
                observed_at=date(2026, 8, 15),
                median_price=None,
                tcg_price=None,
                last_sold_price=None,
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

        assert result == {"updated": 0, "skipped": 1, "total": 1}

    def test_multiple_entries_mixed(self):
        """Handles a mix of updatable and skippable entries."""
        engine = _make_engine()
        with Session(engine) as session:
            # Card 1: has price observations
            _seed_card(session, card_id=1, name="Card A")
            _seed_source_card(session, card_id=1, source="liga", external_id="liga_1")
            _seed_observation(
                session,
                source="liga",
                external_id="liga_1",
                observed_at=date(2026, 8, 15),
                median_price=Decimal("10.00"),
            )
            # Card 2: no price observations
            _seed_card(session, card_id=2, name="Card B")
            _seed_source_card(session, card_id=2, source="liga", external_id="liga_2")

            # Entry 1: should be updated
            _seed_collection_entry(
                session,
                user_id="user1",
                card_id=1,
                created_at=datetime(2026, 8, 15),
            )
            # Entry 2: should be skipped (no observations)
            _seed_collection_entry(
                session,
                user_id="user1",
                card_id=2,
                created_at=datetime(2026, 8, 15),
            )
            # Entry 3: should be skipped (no card_id)
            _seed_collection_entry(
                session,
                user_id="user1",
                card_id=None,
                created_at=datetime(2026, 8, 15),
            )
            session.commit()

        repo = FakeRepo(engine)
        result = backfill_acquisition_prices(repo)

        assert result == {"updated": 1, "skipped": 2, "total": 3}
