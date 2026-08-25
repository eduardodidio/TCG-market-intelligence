"""Unit tests for Repository.get_liga_coverage_stats and get_liga_missing_cards."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from src.database.models import PriceObservationRow, UserCollectionRow
from src.database.repository import Repository


def _make_repo() -> Repository:
    return Repository(db_url="sqlite:///:memory:")


def _seed_collection(repo: Repository, user_id: str = "eduardo") -> list[int]:
    """Seed 3 linked entries + 1 unlinked. Returns list of entry IDs."""
    from sqlalchemy.orm import Session

    entry_ids: list[int] = []
    with Session(repo.engine) as session:
        # Linked entries with card_id
        for i, name in enumerate(["Lightning Bolt", "Dark Ritual", "Counterspell"], start=1):
            row = UserCollectionRow(
                user_id=user_id,
                card_id=i * 10,
                set_code="LEA",
                collector_number=str(i),
                name_en=name,
                quantity=1,
            )
            session.add(row)
            session.flush()
            entry_ids.append(row.id)

        # Unlinked entry
        unlinked = UserCollectionRow(
            user_id=user_id,
            card_id=None,
            set_code="LEA",
            collector_number="99",
            name_en="Unlinked Card",
            quantity=1,
        )
        session.add(unlinked)
        session.flush()
        entry_ids.append(unlinked.id)

        session.commit()
    return entry_ids


def _add_liga_price(repo: Repository, card_id: int, obs_date: date) -> None:
    from sqlalchemy.orm import Session

    with Session(repo.engine) as session:
        obs = PriceObservationRow(
            source="liga",
            external_id=f"liga_{card_id}",
            observed_at=obs_date,
            median_price=Decimal("5.00"),
            currency="BRL",
        )
        session.add(obs)
        session.commit()


class TestGetLigaCoverageStats:
    def test_empty_collection(self):
        repo = _make_repo()
        stats = repo.get_liga_coverage_stats("nobody")
        assert stats["total_cards"] == 0
        assert stats["liga_priced"] == 0
        assert stats["liga_missing"] == 0
        assert stats["liga_stale"] == 0
        assert stats["unlinked"] == 0
        assert stats["coverage_pct"] == 0.0

    def test_all_missing(self):
        repo = _make_repo()
        _seed_collection(repo)
        stats = repo.get_liga_coverage_stats("eduardo")
        assert stats["total_cards"] == 3  # 3 linked
        assert stats["liga_missing"] == 3
        assert stats["liga_priced"] == 0
        assert stats["unlinked"] == 1
        assert stats["coverage_pct"] == 0.0

    def test_partial_coverage(self):
        repo = _make_repo()
        _seed_collection(repo)
        _add_liga_price(repo, 10, date.today())
        stats = repo.get_liga_coverage_stats("eduardo")
        assert stats["total_cards"] == 3
        assert stats["liga_priced"] == 1
        assert stats["liga_missing"] == 2
        assert stats["coverage_pct"] == round(1 / 3 * 100, 1)

    def test_stale_detection(self):
        repo = _make_repo()
        _seed_collection(repo)
        # Add a liga price 10 days ago (stale with default 7d)
        old_date = date.today() - timedelta(days=10)
        _add_liga_price(repo, 10, old_date)
        # Add a fresh liga price
        _add_liga_price(repo, 20, date.today())

        stats = repo.get_liga_coverage_stats("eduardo", stale_days=7)
        assert stats["liga_priced"] == 1  # Dark Ritual
        assert stats["liga_stale"] == 1  # Lightning Bolt
        assert stats["liga_missing"] == 1  # Counterspell

    def test_full_coverage(self):
        repo = _make_repo()
        _seed_collection(repo)
        for card_id in [10, 20, 30]:
            _add_liga_price(repo, card_id, date.today())
        stats = repo.get_liga_coverage_stats("eduardo")
        assert stats["liga_priced"] == 3
        assert stats["liga_missing"] == 0
        assert stats["coverage_pct"] == 100.0

    def test_last_liga_scan(self):
        repo = _make_repo()
        _seed_collection(repo)
        _add_liga_price(repo, 10, date.today())
        stats = repo.get_liga_coverage_stats("eduardo")
        assert stats["last_liga_scan"] == str(date.today())

    def test_no_last_scan(self):
        repo = _make_repo()
        stats = repo.get_liga_coverage_stats("nobody")
        assert stats["last_liga_scan"] is None


class TestGetLigaMissingCards:
    def test_returns_only_missing(self):
        repo = _make_repo()
        _seed_collection(repo)
        _add_liga_price(repo, 10, date.today())

        cards, total = repo.get_liga_missing_cards("eduardo")
        assert total == 2
        names = {c["name_en"] for c in cards}
        assert "Dark Ritual" in names
        assert "Counterspell" in names
        assert "Lightning Bolt" not in names

    def test_includes_stale(self):
        repo = _make_repo()
        _seed_collection(repo)
        old_date = date.today() - timedelta(days=10)
        _add_liga_price(repo, 10, old_date)

        cards, total = repo.get_liga_missing_cards("eduardo", stale_days=7)
        assert total == 3  # All missing: LB is stale, DR and CS have no price
        names = {c["name_en"] for c in cards}
        assert "Lightning Bolt" in names

    def test_pagination(self):
        repo = _make_repo()
        _seed_collection(repo)

        cards, total = repo.get_liga_missing_cards("eduardo", limit=2, offset=0)
        assert total == 3
        assert len(cards) == 2

        cards2, total2 = repo.get_liga_missing_cards("eduardo", limit=2, offset=2)
        assert total2 == 3
        assert len(cards2) == 1

    def test_empty_collection(self):
        repo = _make_repo()
        cards, total = repo.get_liga_missing_cards("nobody")
        assert total == 0
        assert cards == []

    def test_excludes_unlinked(self):
        """Unlinked entries (card_id IS NULL) should not appear in missing list."""
        repo = _make_repo()
        _seed_collection(repo)  # 3 linked + 1 unlinked
        cards, total = repo.get_liga_missing_cards("eduardo")
        assert total == 3  # Only linked entries
        # The unlinked entry should not be present
        for c in cards:
            assert c["card_id"] is not None
