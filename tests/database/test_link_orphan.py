"""Tests for N+1 fix in link_orphan_source_cards (F99-T05)."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import CardRow, SourceCardRow
from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_link_orphan.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


def _seed_cards_and_orphans(repo, count=5):
    """Create `count` cards and matching orphan source_cards."""
    with Session(repo.engine) as session:
        for i in range(count):
            card = CardRow(
                game="magic",
                name_en=f"Card {i}",
                set_code=f"set{i}",
                collector_number=str(i),
            )
            session.add(card)
            session.flush()
            # Orphan source_card (card_id=None) that matches this card
            sc = SourceCardRow(
                source="myp",
                external_id=f"ext{i}",
                card_id=None,
                url=f"http://example.com/{i}",
                set_code=f"set{i}",
                collector_number=str(i),
            )
            session.add(sc)
        session.commit()


class TestLinkOrphanSourceCards:
    def test_links_all_orphans_in_single_call(self, repo):
        _seed_cards_and_orphans(repo, count=5)
        linked = repo.link_orphan_source_cards()
        assert linked == 5

        # Verify all are linked
        with Session(repo.engine) as session:
            orphans = (
                session.execute(select(SourceCardRow).where(SourceCardRow.card_id.is_(None)))
                .scalars()
                .all()
            )
            assert len(orphans) == 0

    def test_orphan_with_no_matching_card_remains_null(self, repo):
        with Session(repo.engine) as session:
            sc = SourceCardRow(
                source="myp",
                external_id="no_match",
                card_id=None,
                url="http://example.com/no_match",
                set_code="nonexistent",
                collector_number="999",
            )
            session.add(sc)
            session.commit()

        linked = repo.link_orphan_source_cards()
        assert linked == 0

        with Session(repo.engine) as session:
            sc = session.execute(
                select(SourceCardRow).where(SourceCardRow.external_id == "no_match")
            ).scalar_one()
            assert sc.card_id is None

    def test_orphan_with_null_set_code_skipped(self, repo):
        with Session(repo.engine) as session:
            sc = SourceCardRow(
                source="myp",
                external_id="null_set",
                card_id=None,
                url="http://example.com/null_set",
                set_code=None,
                collector_number="1",
            )
            session.add(sc)
            session.commit()

        linked = repo.link_orphan_source_cards()
        assert linked == 0

    def test_orphan_with_null_collector_number_skipped(self, repo):
        with Session(repo.engine) as session:
            sc = SourceCardRow(
                source="myp",
                external_id="null_cn",
                card_id=None,
                url="http://example.com/null_cn",
                set_code="2xm",
                collector_number=None,
            )
            session.add(sc)
            session.commit()

        linked = repo.link_orphan_source_cards()
        assert linked == 0

    def test_already_linked_not_modified(self, repo):
        with Session(repo.engine) as session:
            card = CardRow(game="magic", name_en="Bolt", set_code="2xm", collector_number="1")
            session.add(card)
            session.flush()
            sc = SourceCardRow(
                source="myp",
                external_id="already_linked",
                card_id=card.id,
                url="http://example.com/linked",
                set_code="2xm",
                collector_number="1",
            )
            session.add(sc)
            session.commit()
            original_card_id = card.id

        linked = repo.link_orphan_source_cards()
        assert linked == 0

        with Session(repo.engine) as session:
            sc = session.execute(
                select(SourceCardRow).where(SourceCardRow.external_id == "already_linked")
            ).scalar_one()
            assert sc.card_id == original_card_id
