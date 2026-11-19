"""Tests for web card search PT/EN name fallback (F113-T04)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.api.routers.card_search import _find_alternate_name, _search_via_myp
from src.database.models import Base, CardRow
from src.database.repository import Repository

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo_with_cards():
    """In-memory SQLite repo seeded with one card that has both EN and PT names."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            CardRow(
                game="magic",
                name_en="Mox Amber",
                name_pt="Mox de Ambar",
                set_code="dom",
                collector_number="224",
            )
        )
        session.add(
            CardRow(
                game="magic",
                name_en="Lightning Bolt",
                name_pt=None,  # no PT name
                set_code="m10",
                collector_number="146",
            )
        )
        session.commit()
    repo = Repository.__new__(Repository)
    repo.engine = engine
    return repo


# ---------------------------------------------------------------------------
# _find_alternate_name tests
# ---------------------------------------------------------------------------


class TestFindAlternateName:
    def test_pt_query_returns_en(self, repo_with_cards: Repository):
        result = _find_alternate_name(repo_with_cards, "Mox de Ambar")
        assert result == "Mox Amber"

    def test_en_query_returns_pt(self, repo_with_cards: Repository):
        result = _find_alternate_name(repo_with_cards, "Mox Amber")
        assert result == "Mox de Ambar"

    def test_case_insensitive(self, repo_with_cards: Repository):
        result = _find_alternate_name(repo_with_cards, "mox de ambar")
        assert result == "Mox Amber"

    def test_unknown_query_returns_none(self, repo_with_cards: Repository):
        result = _find_alternate_name(repo_with_cards, "Nonexistent Card")
        assert result is None

    def test_en_card_without_pt_returns_none(self, repo_with_cards: Repository):
        result = _find_alternate_name(repo_with_cards, "Lightning Bolt")
        assert result is None

    def test_whitespace_stripped(self, repo_with_cards: Repository):
        result = _find_alternate_name(repo_with_cards, "  Mox de Ambar  ")
        assert result == "Mox Amber"


# ---------------------------------------------------------------------------
# _search_via_myp fallback tests
# ---------------------------------------------------------------------------


class TestSearchViaMypFallback:
    @pytest.mark.asyncio
    async def test_retries_with_alternate_name_on_empty(self, repo_with_cards: Repository):
        """When MYP returns empty for PT name, retry with EN."""
        myp = AsyncMock()
        mock_result = MagicMock()
        mock_result.name = "Mox Amber"
        mock_result.image_url = "https://example.com/mox.jpg"
        myp.search_card = AsyncMock(
            side_effect=[
                [],  # First call empty
                [mock_result],  # Retry succeeds
            ]
        )

        response = await _search_via_myp(myp, "Mox de Ambar", repo_with_cards)
        assert myp.search_card.call_count == 2
        assert len(response.data) == 1
        assert response.data[0].card_name == "Mox Amber"

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_alternate(self, repo_with_cards: Repository):
        myp = AsyncMock()
        myp.search_card = AsyncMock(return_value=[])

        response = await _search_via_myp(myp, "Unknown Card XYZ", repo_with_cards)
        assert myp.search_card.call_count == 1
        assert response.data == []
