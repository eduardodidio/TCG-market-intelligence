"""Tests for atomic transaction wrapper (F99-T06)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.models import (
    CardRow,
    PriceObservationRow,
    SourceCardRow,
    UserCollectionRow,
)
from src.database.repository import Repository
from src.domain.models import CardIdentity, HistoricalPrice, SourceCard


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_txn.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


def _make_source_card() -> SourceCard:
    return SourceCard(
        source="myp",
        external_id="ext_txn_1",
        url="http://example.com/txn1",
        sku="magic_2xm_1",
        identity=CardIdentity(
            game="magic",
            name_en="Lightning Bolt",
            name_pt="Raio",
            set_code="2xm",
            collector_number="1",
        ),
    )


def _make_prices() -> list[HistoricalPrice]:
    return [
        HistoricalPrice(
            source="myp",
            external_id="ext_txn_1",
            observed_at=date(2026, 1, 1),
            median_price=Decimal("10.00"),
            currency="BRL",
        ),
        HistoricalPrice(
            source="myp",
            external_id="ext_txn_1",
            observed_at=date(2026, 1, 2),
            median_price=Decimal("11.00"),
            currency="BRL",
        ),
    ]


class TestTransactionContextManager:
    def test_successful_transaction_commits_all(self, repo):
        sc = _make_source_card()
        prices = _make_prices()

        # Create a collection entry to link
        with Session(repo.engine) as session:
            entry = UserCollectionRow(user_id="user1", set_code="2xm", collector_number="1")
            session.add(entry)
            session.commit()
            entry_id = entry.id

        with repo.transaction() as txn:
            card_id = repo.upsert_card(sc, session=txn)
            repo.upsert_source_card(sc, card_id=card_id, session=txn)
            inserted = repo.insert_price_observations(prices, session=txn)
            repo.link_collection_entry(entry_id, card_id, session=txn)

        assert card_id is not None
        assert inserted == 2

        # Verify all data committed
        with Session(repo.engine) as session:
            cards = session.execute(select(func.count()).select_from(CardRow)).scalar()
            assert cards == 1
            obs = session.execute(select(func.count()).select_from(PriceObservationRow)).scalar()
            assert obs == 2
            entry = session.get(UserCollectionRow, entry_id)
            assert entry.card_id == card_id

    def test_failed_transaction_rolls_back_all(self, repo):
        sc = _make_source_card()
        prices = _make_prices()

        with Session(repo.engine) as session:
            entry = UserCollectionRow(user_id="user1", set_code="2xm", collector_number="1")
            session.add(entry)
            session.commit()

        with pytest.raises(ValueError, match="simulated"):
            with repo.transaction() as txn:
                repo.upsert_card(sc, session=txn)
                repo.upsert_source_card(sc, card_id=1, session=txn)
                repo.insert_price_observations(prices, session=txn)
                raise ValueError("simulated failure in step 3f")

        # Verify nothing committed
        with Session(repo.engine) as session:
            cards = session.execute(select(func.count()).select_from(CardRow)).scalar()
            assert cards == 0
            obs = session.execute(select(func.count()).select_from(PriceObservationRow)).scalar()
            assert obs == 0
            scs = session.execute(select(func.count()).select_from(SourceCardRow)).scalar()
            assert scs == 0

    def test_rollback_re_raises_exception(self, repo):
        with pytest.raises(RuntimeError, match="boom"):
            with repo.transaction():
                raise RuntimeError("boom")

    def test_repo_methods_still_work_without_session(self, repo):
        """Backward compatibility: methods work without explicit session."""
        sc = _make_source_card()
        card_id = repo.upsert_card(sc)
        assert card_id is not None

        sc_id = repo.upsert_source_card(sc, card_id=card_id)
        assert sc_id > 0

        inserted = repo.insert_price_observations(_make_prices())
        assert inserted == 2
