"""Integration tests for FK constraints, cascade behavior, and data integrity (F99-T08/T09)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database.models import (
    CardLegalityRow,
    CardRow,
    CreditBalanceRow,
    CreditTransactionRow,
    DeckCardRow,
    DeckRow,
    EvaluationEntryRow,
    LegalityHistoryRow,
    PriceObservationRow,
    SourceCardRow,
    UserCollectionRow,
    UserRow,
)
from src.database.repository import Repository
from src.domain.models import CardIdentity, HistoricalPrice, SourceCard
from src.services.currency import CurrencyConverter


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_integrity.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


@pytest.fixture()
def seeded_repo(repo):
    """Create a repo with a card, user, deck, and related rows."""
    with Session(repo.engine) as session:
        # Card
        card = CardRow(game="magic", name_en="Lightning Bolt", set_code="2xm", collector_number="1")
        session.add(card)
        session.flush()

        # User
        user = UserRow(email="test@integrity.com", auth_provider="email", password_hash="hash")
        session.add(user)
        session.flush()

        # Deck
        deck = DeckRow(user_id=str(user.id), name="Test Deck")
        session.add(deck)
        session.flush()

        # Collection entry
        entry = UserCollectionRow(
            user_id=str(user.id),
            card_id=card.id,
            set_code="2xm",
            collector_number="1",
        )
        session.add(entry)
        session.flush()

        # Source card
        sc = SourceCardRow(
            source="myp",
            external_id="ext1",
            card_id=card.id,
            url="http://example.com/1",
            set_code="2xm",
            collector_number="1",
        )
        session.add(sc)

        # Deck card linked to the card
        dc = DeckCardRow(
            deck_id=deck.id,
            card_id=card.id,
            name_en="Lightning Bolt",
        )
        session.add(dc)

        # Card legality
        leg = CardLegalityRow(card_id=card.id, format="commander", status="legal")
        session.add(leg)

        # Legality history
        lh = LegalityHistoryRow(
            card_id=card.id,
            format="commander",
            new_status="legal",
            changed_at=datetime.now(),
        )
        session.add(lh)

        # Evaluation entry
        ev = EvaluationEntryRow(
            user_id=user.id,
            card_name="Lightning Bolt",
            card_id=card.id,
        )
        session.add(ev)

        # Credit balance
        cb = CreditBalanceRow(user_id=user.id, balance=100)
        session.add(cb)

        # Credit transaction
        ct = CreditTransactionRow(user_id=user.id, amount=50, reason="seed")
        session.add(ct)

        session.commit()

    return repo


# ─── Group 1: FK Constraint Enforcement ─────────────────────────────


class TestForeignKeyEnforcement:
    """Verify that FK constraints are enforced at the database level."""

    def test_source_card_invalid_card_id_rejected(self, repo):
        with Session(repo.engine) as session:
            session.add(
                SourceCardRow(source="myp", external_id="bad", card_id=99999, url="http://x.com")
            )
            with pytest.raises(IntegrityError):
                session.commit()

    def test_deck_card_invalid_deck_id_rejected(self, seeded_repo):
        with Session(seeded_repo.engine) as session:
            session.add(DeckCardRow(deck_id=99999, card_id=None, name_en="Bad"))
            with pytest.raises(IntegrityError):
                session.commit()

    def test_deck_card_invalid_card_id_rejected(self, seeded_repo):
        with Session(seeded_repo.engine) as session:
            deck_id = session.execute(select(DeckRow.id)).scalar()
            session.add(DeckCardRow(deck_id=deck_id, card_id=99999, name_en="Bad"))
            with pytest.raises(IntegrityError):
                session.commit()

    def test_card_legality_invalid_card_id_rejected(self, repo):
        with Session(repo.engine) as session:
            session.add(CardLegalityRow(card_id=99999, format="std", status="legal"))
            with pytest.raises(IntegrityError):
                session.commit()

    def test_source_card_null_card_id_allowed(self, repo):
        with Session(repo.engine) as session:
            sc = SourceCardRow(source="myp", external_id="ok", card_id=None, url="http://x.com")
            session.add(sc)
            session.commit()
            assert sc.id is not None

    def test_deck_card_null_card_id_allowed(self, seeded_repo):
        with Session(seeded_repo.engine) as session:
            deck_id = session.execute(select(DeckRow.id)).scalar()
            dc = DeckCardRow(deck_id=deck_id, card_id=None, name_en="Unlinked")
            session.add(dc)
            session.commit()
            assert dc.id is not None


# ─── Group 2: CASCADE DELETE ─────────────────────────────────────────


class TestCascadeDelete:
    """Verify ON DELETE CASCADE propagates correctly."""

    def test_delete_card_cascades_to_legalities(self, seeded_repo):
        with Session(seeded_repo.engine) as session:
            card = session.execute(select(CardRow)).scalar_one()
            card_id = card.id

            # Verify legality exists
            count_before = session.execute(
                select(func.count())
                .select_from(CardLegalityRow)
                .where(CardLegalityRow.card_id == card_id)
            ).scalar()
            assert count_before == 1

            session.delete(card)
            session.commit()

            # Legality should be deleted by cascade
            count_after = session.execute(
                select(func.count())
                .select_from(CardLegalityRow)
                .where(CardLegalityRow.card_id == card_id)
            ).scalar()
            assert count_after == 0

    def test_delete_card_cascades_to_legality_history(self, seeded_repo):
        with Session(seeded_repo.engine) as session:
            card = session.execute(select(CardRow)).scalar_one()
            card_id = card.id
            session.delete(card)
            session.commit()

            count = session.execute(
                select(func.count())
                .select_from(LegalityHistoryRow)
                .where(LegalityHistoryRow.card_id == card_id)
            ).scalar()
            assert count == 0

    def test_delete_deck_cascades_to_deck_cards(self, seeded_repo):
        with Session(seeded_repo.engine) as session:
            deck = session.execute(select(DeckRow)).scalar_one()
            deck_id = deck.id

            count_before = session.execute(
                select(func.count()).select_from(DeckCardRow).where(DeckCardRow.deck_id == deck_id)
            ).scalar()
            assert count_before == 1

            session.delete(deck)
            session.commit()

            count_after = session.execute(
                select(func.count()).select_from(DeckCardRow).where(DeckCardRow.deck_id == deck_id)
            ).scalar()
            assert count_after == 0


# ─── Group 3: SET NULL on Delete ─────────────────────────────────────


class TestSetNullOnDelete:
    """Verify ON DELETE SET NULL works for nullable FK columns."""

    def test_delete_card_sets_null_on_source_cards(self, seeded_repo):
        with Session(seeded_repo.engine) as session:
            card = session.execute(select(CardRow)).scalar_one()
            sc_before = session.execute(
                select(SourceCardRow).where(SourceCardRow.card_id == card.id)
            ).scalar_one()
            assert sc_before.card_id is not None

            session.delete(card)
            session.commit()

            sc_after = session.execute(
                select(SourceCardRow).where(SourceCardRow.external_id == "ext1")
            ).scalar_one()
            assert sc_after.card_id is None

    def test_delete_card_sets_null_on_deck_cards(self, seeded_repo):
        with Session(seeded_repo.engine) as session:
            card = session.execute(select(CardRow)).scalar_one()
            session.delete(card)
            session.commit()

            dc = session.execute(
                select(DeckCardRow).where(DeckCardRow.name_en == "Lightning Bolt")
            ).scalar_one()
            assert dc.card_id is None

    def test_delete_card_sets_null_on_user_collection(self, seeded_repo):
        with Session(seeded_repo.engine) as session:
            card = session.execute(select(CardRow)).scalar_one()
            session.delete(card)
            session.commit()

            entry = session.execute(
                select(UserCollectionRow).where(UserCollectionRow.collector_number == "1")
            ).scalar_one()
            assert entry.card_id is None

    def test_delete_card_sets_null_on_evaluation_entries(self, seeded_repo):
        with Session(seeded_repo.engine) as session:
            card = session.execute(select(CardRow)).scalar_one()
            session.delete(card)
            session.commit()

            ev = session.execute(
                select(EvaluationEntryRow).where(EvaluationEntryRow.card_name == "Lightning Bolt")
            ).scalar_one()
            assert ev.card_id is None


# ─── Group 4: Sync Pipeline Atomicity ────────────────────────────────


class TestSyncAtomicity:
    """Verify the sync pipeline transaction wrapper from T06."""

    def test_successful_sync_commits_all(self, repo):
        sc = SourceCard(
            source="myp",
            external_id="sync1",
            url="http://example.com/sync1",
            sku="magic_2xm_1",
            identity=CardIdentity(
                game="magic",
                name_en="Counterspell",
                set_code="2xm",
                collector_number="2",
            ),
        )
        prices = [
            HistoricalPrice(
                source="myp",
                external_id="sync1",
                observed_at=date(2026, 1, 1),
                median_price=Decimal("5.00"),
                currency="BRL",
            )
        ]

        with Session(repo.engine) as session:
            entry = UserCollectionRow(user_id="u1", set_code="2xm", collector_number="2")
            session.add(entry)
            session.commit()
            entry_id = entry.id

        with repo.transaction() as txn:
            card_id = repo.upsert_card(sc, session=txn)
            repo.upsert_source_card(sc, card_id=card_id, session=txn)
            repo.insert_price_observations(prices, session=txn)
            repo.link_collection_entry(entry_id, card_id, session=txn)

        with Session(repo.engine) as session:
            assert session.execute(select(func.count()).select_from(CardRow)).scalar() == 1
            assert (
                session.execute(select(func.count()).select_from(PriceObservationRow)).scalar() == 1
            )
            e = session.get(UserCollectionRow, entry_id)
            assert e.card_id == card_id

    def test_failed_sync_rolls_back_all(self, repo):
        sc = SourceCard(
            source="myp",
            external_id="sync2",
            url="http://example.com/sync2",
            identity=CardIdentity(
                game="magic",
                name_en="Force",
                set_code="all",
                collector_number="1",
            ),
        )

        with pytest.raises(RuntimeError):
            with repo.transaction() as txn:
                repo.upsert_card(sc, session=txn)
                raise RuntimeError("simulated failure")

        with Session(repo.engine) as session:
            assert session.execute(select(func.count()).select_from(CardRow)).scalar() == 0


# ─── Group 5: Exchange Rate Fallback ─────────────────────────────────


class TestExchangeRateFallback:
    """Verify the exchange rate fallback logic from T07."""

    def _seed_rate(self, repo, d: date, rate: Decimal = Decimal("5.50")):
        from src.database.models import ExchangeRateRow

        with Session(repo.engine) as session:
            session.add(
                ExchangeRateRow(
                    rate_date=d,
                    from_currency="USD",
                    to_currency="BRL",
                    rate=rate,
                    source="test",
                )
            )
            session.commit()

    def test_exact_date_match(self, repo):
        self._seed_rate(repo, date(2026, 1, 15))
        row = repo.get_closest_rate(date(2026, 1, 15))
        assert row is not None
        assert row.rate_date == date(2026, 1, 15)

    def test_fallback_to_earlier_date(self, repo):
        self._seed_rate(repo, date(2026, 1, 13))
        row = repo.get_closest_rate(date(2026, 1, 15))
        assert row is not None
        assert row.rate_date == date(2026, 1, 13)

    def test_fallback_to_later_date_when_no_earlier(self, repo):
        self._seed_rate(repo, date(2026, 1, 18))
        row = repo.get_closest_rate(date(2026, 1, 15))
        assert row is not None
        assert row.rate_date == date(2026, 1, 18)

    def test_gap_exceeds_max_returns_none(self, repo):
        self._seed_rate(repo, date(2026, 1, 1))
        row = repo.get_closest_rate(date(2026, 1, 15))
        assert row is None

    def test_converter_fallback_to_brl(self, repo):
        converter = CurrencyConverter(repo)
        result = converter.convert(Decimal("100.00"), date(2026, 6, 1), "USD", fallback_to_brl=True)
        assert result == Decimal("100.00")


# ─── Group 6: Orphan Linking (single query) ──────────────────────────


class TestOrphanLinking:
    """Verify the N+1-fixed link_orphan_source_cards from T05."""

    def test_links_all_orphans_in_single_call(self, repo):
        with Session(repo.engine) as session:
            for i in range(3):
                card = CardRow(
                    game="magic",
                    name_en=f"Card {i}",
                    set_code=f"s{i}",
                    collector_number=str(i),
                )
                session.add(card)
                session.flush()
                session.add(
                    SourceCardRow(
                        source="myp",
                        external_id=f"orphan{i}",
                        card_id=None,
                        url=f"http://x.com/{i}",
                        set_code=f"s{i}",
                        collector_number=str(i),
                    )
                )
            session.commit()

        linked = repo.link_orphan_source_cards()
        assert linked == 3

        with Session(repo.engine) as session:
            nulls = session.execute(
                select(func.count())
                .select_from(SourceCardRow)
                .where(SourceCardRow.card_id.is_(None))
            ).scalar()
            assert nulls == 0

    def test_skips_orphans_with_null_set_code(self, repo):
        with Session(repo.engine) as session:
            session.add(
                SourceCardRow(
                    source="myp",
                    external_id="no_set",
                    card_id=None,
                    url="http://x.com/ns",
                    set_code=None,
                    collector_number="1",
                )
            )
            session.commit()

        linked = repo.link_orphan_source_cards()
        assert linked == 0

    def test_does_not_modify_already_linked(self, repo):
        with Session(repo.engine) as session:
            card = CardRow(game="magic", name_en="Bolt", set_code="2xm", collector_number="1")
            session.add(card)
            session.flush()
            session.add(
                SourceCardRow(
                    source="myp",
                    external_id="linked",
                    card_id=card.id,
                    url="http://x.com/l",
                    set_code="2xm",
                    collector_number="1",
                )
            )
            session.commit()

        linked = repo.link_orphan_source_cards()
        assert linked == 0


# ─── Group 7: Collection Deletion Behavior ───────────────────────────


class TestCollectionDeletionBehavior:
    """Verify that deleting a collection entry preserves related data."""

    def test_delete_collection_entry_preserves_deck_cards(self, seeded_repo):
        with Session(seeded_repo.engine) as session:
            entry = session.execute(select(UserCollectionRow)).scalar_one()
            user_id = entry.user_id
            entry_id = entry.id
            card_id = entry.card_id

        seeded_repo.delete_collection_entry(entry_id, user_id)

        with Session(seeded_repo.engine) as session:
            # Deck card should still exist with card_id intact
            # (no FK from deck_cards to user_collection)
            dc = session.execute(
                select(DeckCardRow).where(DeckCardRow.name_en == "Lightning Bolt")
            ).scalar_one()
            assert dc.card_id == card_id

    def test_delete_collection_entry_preserves_price_observations(self, seeded_repo):
        # Add a price observation first
        with Session(seeded_repo.engine) as session:
            session.add(
                PriceObservationRow(
                    source="myp",
                    external_id="ext1",
                    observed_at=date(2026, 1, 1),
                    median_price=Decimal("10.00"),
                    currency="BRL",
                )
            )
            session.commit()

        with Session(seeded_repo.engine) as session:
            entry = session.execute(select(UserCollectionRow)).scalar_one()
            user_id = entry.user_id
            entry_id = entry.id

        seeded_repo.delete_collection_entry(entry_id, user_id)

        with Session(seeded_repo.engine) as session:
            obs_count = session.execute(
                select(func.count()).select_from(PriceObservationRow)
            ).scalar()
            assert obs_count == 1

    def test_bulk_delete_preserves_deck_cards(self, seeded_repo):
        with Session(seeded_repo.engine) as session:
            entry = session.execute(select(UserCollectionRow)).scalar_one()
            user_id = entry.user_id
            entry_id = entry.id
            card_id = entry.card_id

        seeded_repo.bulk_delete_collection_entries([entry_id], user_id)

        with Session(seeded_repo.engine) as session:
            dc = session.execute(
                select(DeckCardRow).where(DeckCardRow.name_en == "Lightning Bolt")
            ).scalar_one()
            assert dc.card_id == card_id

    def test_delete_card_row_sets_null_on_deck_cards(self, seeded_repo):
        """FK cascade from T04: deleting a CardRow sets deck_cards.card_id = NULL."""
        with Session(seeded_repo.engine) as session:
            card = session.execute(select(CardRow)).scalar_one()
            session.delete(card)
            session.commit()

            dc = session.execute(
                select(DeckCardRow).where(DeckCardRow.name_en == "Lightning Bolt")
            ).scalar_one()
            assert dc.card_id is None
