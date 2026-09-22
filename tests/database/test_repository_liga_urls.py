"""Tests for Liga card URL repository methods (F169-T03)."""

from __future__ import annotations

import pytest

from src.database.models import CardRow
from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "t.db"
    return Repository(f"sqlite:///{db_path}")


def _seed_card(repo, card_id: int, name_en: str) -> CardRow:
    """Insert a card row directly and return it."""
    from sqlalchemy.orm import Session

    with Session(repo.engine) as session:
        card = CardRow(id=card_id, game="magic", name_en=name_en)
        session.add(card)
        session.commit()
        session.refresh(card)
        session.expunge(card)
        return card


class TestGetAllLigaCardUrls:
    def test_returns_empty_when_no_urls(self, repo):
        result = repo.get_all_liga_card_urls()
        assert result == []

    def test_returns_all_urls(self, repo):
        repo.upsert_liga_card_url("liga_1", "https://liga.com/card1")
        repo.upsert_liga_card_url("liga_2", "https://liga.com/card2")
        repo.upsert_liga_card_url("liga_3_foil", "https://liga.com/card3")

        result = repo.get_all_liga_card_urls()
        assert len(result) == 3
        ext_ids = {r.external_id for r in result}
        assert ext_ids == {"liga_1", "liga_2", "liga_3_foil"}

    def test_returned_rows_are_detached(self, repo):
        """Rows should be usable outside the session (expunged)."""
        repo.upsert_liga_card_url("liga_1", "https://liga.com/card1")
        result = repo.get_all_liga_card_urls()
        # Access attributes outside session — should not raise
        assert result[0].external_id == "liga_1"
        assert result[0].url == "https://liga.com/card1"


class TestGetCardNameByLigaExternalId:
    def test_returns_name_for_existing_card(self, repo):
        _seed_card(repo, 42, "Sol Ring")
        name = repo.get_card_name_by_liga_external_id("liga_42")
        assert name == "Sol Ring"

    def test_returns_name_for_foil_external_id(self, repo):
        _seed_card(repo, 42, "Sol Ring")
        name = repo.get_card_name_by_liga_external_id("liga_42_foil")
        assert name == "Sol Ring"

    def test_returns_none_for_missing_card(self, repo):
        name = repo.get_card_name_by_liga_external_id("liga_9999")
        assert name is None

    def test_returns_none_for_invalid_external_id(self, repo):
        name = repo.get_card_name_by_liga_external_id("invalid_format")
        assert name is None

    def test_returns_none_for_non_numeric_id(self, repo):
        name = repo.get_card_name_by_liga_external_id("liga_abc")
        assert name is None
