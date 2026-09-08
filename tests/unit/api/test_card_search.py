"""Tests for web card search PT/EN name fallback (F113-T04)."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.api.routers.card_search import _find_alternate_name, _search_via_liga, _search_via_myp
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
# _search_via_liga fallback tests
# ---------------------------------------------------------------------------


class TestSearchViaLigaFallback:
    @pytest.mark.asyncio
    async def test_retries_with_alternate_name_on_empty(self, repo_with_cards: Repository):
        """When Liga returns empty for PT name, retry with EN and return results."""
        liga = AsyncMock()
        # First call (PT) -> empty, second call (EN) -> prices
        liga.search_card = AsyncMock(
            side_effect=[
                {"normal": {}, "foil": {}, "card_name": ""},
                {
                    "normal": {"low": Decimal("10.00")},
                    "foil": {},
                    "card_name": "Mox Amber",
                },
            ]
        )

        response = await _search_via_liga(liga, "Mox de Ambar", repo_with_cards)
        assert liga.search_card.call_count == 2
        assert liga.search_card.call_args_list[1][0][0] == "Mox Amber"
        assert response.data[0].card_name == "Mox Amber"
        assert response.data[0].normal_price == 10.0

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_alternate(self, repo_with_cards: Repository):
        """When Liga returns empty and no alternate name exists, return empty."""
        liga = AsyncMock()
        liga.search_card = AsyncMock(return_value={"normal": {}, "foil": {}})

        response = await _search_via_liga(liga, "Unknown Card XYZ", repo_with_cards)
        assert liga.search_card.call_count == 1
        assert response.data == []

    @pytest.mark.asyncio
    async def test_no_extra_credits_for_retry(self, repo_with_cards: Repository):
        """The retry path does NOT deduct additional credits (credit deduction
        happens only in the endpoint, not in _search_via_liga)."""
        liga = AsyncMock()
        liga.search_card = AsyncMock(
            side_effect=[
                {"normal": {}, "foil": {}},
                {"normal": {"low": Decimal("5.00")}, "foil": {}, "card_name": "Mox Amber"},
            ]
        )

        # _search_via_liga never touches credit_svc — it has no such parameter
        response = await _search_via_liga(liga, "Mox de Ambar", repo_with_cards)
        assert len(response.data) == 1

    @pytest.mark.asyncio
    async def test_retry_failure_returns_empty(self, repo_with_cards: Repository):
        """When the retry itself fails (timeout/exception), return empty gracefully."""
        liga = AsyncMock()
        liga.search_card = AsyncMock(
            side_effect=[
                {"normal": {}, "foil": {}},
                Exception("connection error"),
            ]
        )

        response = await _search_via_liga(liga, "Mox de Ambar", repo_with_cards)
        assert response.data == []

    @pytest.mark.asyncio
    async def test_no_retry_when_first_call_has_results(self, repo_with_cards: Repository):
        """When Liga returns results on first try, no fallback is triggered."""
        liga = AsyncMock()
        liga.search_card = AsyncMock(
            return_value={
                "normal": {"low": Decimal("10.00")},
                "foil": {},
                "card_name": "Mox de Ambar",
            }
        )

        response = await _search_via_liga(liga, "Mox de Ambar", repo_with_cards)
        assert liga.search_card.call_count == 1
        assert len(response.data) == 1


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
