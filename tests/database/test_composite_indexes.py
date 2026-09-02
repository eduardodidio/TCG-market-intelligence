"""Tests for composite indexes (F99-T02)."""

from __future__ import annotations

import pytest
from sqlalchemy import inspect

from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_indexes.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


def _get_index_names(repo, table_name: str) -> set[str]:
    """Return set of index names for a given table."""
    insp = inspect(repo.engine)
    indexes = insp.get_indexes(table_name)
    return {idx["name"] for idx in indexes}


class TestCompositeIndexes:
    def test_user_collection_user_card_index_exists(self, repo):
        names = _get_index_names(repo, "user_collection")
        assert "ix_user_collection_user_card" in names

    def test_deck_cards_deck_card_index_exists(self, repo):
        names = _get_index_names(repo, "deck_cards")
        assert "ix_deck_cards_deck_card" in names

    def test_price_obs_extid_date_index_exists(self, repo):
        names = _get_index_names(repo, "price_observations")
        assert "ix_price_obs_extid_date" in names

    def test_source_card_cardid_source_index_exists(self, repo):
        names = _get_index_names(repo, "source_cards")
        assert "ix_source_card_cardid_source" in names


class TestExistingSingleColumnIndexesPreserved:
    """Verify that existing single-column indexes were not accidentally removed."""

    def test_user_collection_user_index(self, repo):
        names = _get_index_names(repo, "user_collection")
        assert "ix_user_collection_user" in names

    def test_user_collection_card_index(self, repo):
        names = _get_index_names(repo, "user_collection")
        assert "ix_user_collection_card" in names

    def test_deck_cards_deck_index(self, repo):
        names = _get_index_names(repo, "deck_cards")
        assert "ix_deck_cards_deck" in names

    def test_deck_cards_card_index(self, repo):
        names = _get_index_names(repo, "deck_cards")
        assert "ix_deck_cards_card" in names

    def test_source_card_sku_index(self, repo):
        names = _get_index_names(repo, "source_cards")
        assert "ix_source_card_sku" in names

    def test_price_obs_card_date_index(self, repo):
        names = _get_index_names(repo, "price_observations")
        assert "ix_price_obs_card_date" in names
