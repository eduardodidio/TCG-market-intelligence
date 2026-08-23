"""Unit tests for src/collectors/bulk_canonize.py."""

from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.collectors.bulk_canonize import bulk_canonize
from src.database.models import UserCollectionRow
from src.providers.myp.exceptions import RateLimitError, ServerError


def _make_collection_row(**overrides) -> MagicMock:
    """Create a mock UserCollectionRow."""
    defaults = {
        "id": 1,
        "user_id": "test-user",
        "card_id": None,
        "set_code": "DMR",
        "collector_number": "123",
        "name_en": "Lightning Bolt",
        "name_pt": "Raio",
        "set_name_en": "Dominaria Remastered",
        "quantity": 1,
        "quality": "NM",
        "language": "EN",
        "rarity": "R",
        "color": "R",
        "extras": None,
        "created_at": datetime(2026, 1, 1),
    }
    defaults.update(overrides)
    row = MagicMock(spec=UserCollectionRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_provider(
    search_results=None,
    details=None,
    price=None,
    search_side_effect=None,
) -> AsyncMock:
    """Create a mock MYP provider."""
    provider = AsyncMock()
    if search_side_effect:
        provider.search_card.side_effect = search_side_effect
    else:
        provider.search_card.return_value = search_results or []
    provider.get_card_details.return_value = details
    provider.fetch_current_price.return_value = price
    provider.close = AsyncMock()
    return provider


def _make_match_result(status="no_match", myp_result=None):
    """Create a mock MatchResult."""
    m = MagicMock()
    m.status = status
    m.myp_result = myp_result
    return m


def _make_repo():
    """Create a mock Repository."""
    repo = MagicMock()
    repo.create_canonical_card.return_value = 100
    return repo


@pytest.mark.asyncio
@patch("src.collectors.bulk_canonize._get_unlinked_entries")
async def test_bulk_canonize_skips_already_linked(mock_get_entries):
    """Entries with card_id and MYP source cards are not returned
    by _get_unlinked_entries, so they never reach canonize."""
    mock_get_entries.return_value = []
    provider = _make_provider()
    engine = MagicMock()

    result = await bulk_canonize(engine, "test-user", provider, repo=_make_repo())

    assert result.total == 0
    assert result.canonized == 0
    assert result.skipped == 0
    provider.search_card.assert_not_called()


@pytest.mark.asyncio
@patch("src.collectors.bulk_canonize.match_collection_card")
@patch("src.collectors.bulk_canonize._get_unlinked_entries")
async def test_bulk_canonize_processes_unlinked(mock_get_entries, mock_match):
    """Entries with card_id=NULL are processed."""
    unlinked = _make_collection_row(id=1, card_id=None)
    mock_get_entries.return_value = [unlinked]
    mock_match.return_value = _make_match_result()
    provider = _make_provider()

    repo = _make_repo()
    engine = MagicMock()

    result = await bulk_canonize(engine, "test-user", provider, repo=repo)

    assert result.total == 1
    assert result.canonized == 1
    repo.create_canonical_card.assert_called_once()
    repo.link_collection_entry.assert_called_once_with(1, 100)


@pytest.mark.asyncio
@patch("src.collectors.bulk_canonize.match_collection_card")
@patch("src.collectors.bulk_canonize._get_unlinked_entries")
async def test_bulk_canonize_handles_orphans(mock_get_entries, mock_match):
    """Entries with card_id but no SourceCardRow are re-processed."""
    orphan = _make_collection_row(id=2, card_id=42)
    mock_get_entries.return_value = [orphan]
    mock_match.return_value = _make_match_result()
    provider = _make_provider()

    repo = _make_repo()
    engine = MagicMock()

    result = await bulk_canonize(engine, "test-user", provider, repo=repo)

    assert result.total == 1
    assert result.canonized == 1
    # Should NOT create a new card (already has card_id)
    repo.create_canonical_card.assert_not_called()
    repo.link_collection_entry.assert_not_called()


@pytest.mark.asyncio
@patch("src.collectors.bulk_canonize.match_collection_card")
@patch("src.collectors.bulk_canonize._get_unlinked_entries")
async def test_bulk_canonize_respects_limit(mock_get_entries, mock_match):
    """When limit=N, only first N entries processed."""
    entries = [_make_collection_row(id=i, card_id=None) for i in range(1, 4)]
    mock_get_entries.return_value = entries[:2]
    mock_match.return_value = _make_match_result()
    provider = _make_provider()

    repo = _make_repo()
    engine = MagicMock()

    result = await bulk_canonize(engine, "test-user", provider, limit=2, repo=repo)

    assert result.total == 2
    mock_get_entries.assert_called_once_with(engine, "test-user", 2)


@pytest.mark.asyncio
@patch("src.collectors.bulk_canonize.match_collection_card")
@patch("src.collectors.bulk_canonize._get_unlinked_entries")
async def test_bulk_canonize_rate_limit_handling(mock_get_entries, mock_match):
    """429 from MYP counted in rate_limited, does not abort batch."""
    entries = [
        _make_collection_row(id=1, card_id=None),
        _make_collection_row(id=2, card_id=None),
    ]
    mock_get_entries.return_value = entries
    mock_match.return_value = _make_match_result()

    # Entry 1: search raises RateLimitError (before PT fallback)
    # Entry 2: EN search returns results (no PT fallback needed)
    provider = _make_provider(
        search_side_effect=[
            RateLimitError("429 Too Many Requests"),
            [MagicMock()],  # EN search returns results, skip PT fallback
        ]
    )

    repo = _make_repo()
    engine = MagicMock()

    result = await bulk_canonize(engine, "test-user", provider, repo=repo)

    assert result.rate_limited == 1
    assert result.canonized == 1
    assert result.total == 2


@pytest.mark.asyncio
@patch("src.collectors.bulk_canonize.match_collection_card")
@patch("src.collectors.bulk_canonize._get_unlinked_entries")
async def test_bulk_canonize_concurrency_semaphore(mock_get_entries, mock_match):
    """Verify semaphore limits parallel calls."""
    entries = [_make_collection_row(id=i, card_id=None) for i in range(1, 6)]
    mock_get_entries.return_value = entries
    mock_match.return_value = _make_match_result()

    max_concurrent = 0
    current_concurrent = 0
    lock = asyncio.Lock()

    async def tracking_search(name):
        nonlocal max_concurrent, current_concurrent
        async with lock:
            current_concurrent += 1
            if current_concurrent > max_concurrent:
                max_concurrent = current_concurrent
        await asyncio.sleep(0.01)
        async with lock:
            current_concurrent -= 1
        return []

    provider = AsyncMock()
    provider.search_card = tracking_search
    provider.close = AsyncMock()

    repo = _make_repo()
    engine = MagicMock()

    result = await bulk_canonize(engine, "test-user", provider, concurrency=2, repo=repo)

    assert max_concurrent <= 2
    assert result.total == 5


@pytest.mark.asyncio
@patch("src.collectors.bulk_canonize.match_collection_card")
@patch("src.collectors.bulk_canonize._get_unlinked_entries")
async def test_bulk_canonize_summary_counts(mock_get_entries, mock_match):
    """Returned summary has correct total/canonized/failed/skipped/rate_limited."""
    entries = [
        _make_collection_row(id=1, card_id=None),
        _make_collection_row(id=2, card_id=None),
        _make_collection_row(id=3, card_id=None),
    ]
    mock_get_entries.return_value = entries
    mock_match.return_value = _make_match_result()

    # Entry 1: EN search returns results (success, no PT fallback)
    # Entry 2: rate limited on EN search
    # Entry 3: server error on EN search
    provider = _make_provider(
        search_side_effect=[
            [MagicMock()],  # Entry 1: EN returns results
            RateLimitError("429"),
            ServerError("500"),
        ]
    )

    repo = _make_repo()
    engine = MagicMock()

    result = await bulk_canonize(engine, "test-user", provider, repo=repo)

    assert result.total == 3
    assert result.canonized == 1
    assert result.rate_limited == 1
    assert result.failed == 1
    assert result.skipped == 0


@pytest.mark.asyncio
@patch("src.collectors.bulk_canonize._get_unlinked_entries")
async def test_bulk_canonize_empty_collection(mock_get_entries):
    """No unlinked entries returns summary with all zeros."""
    mock_get_entries.return_value = []
    provider = _make_provider()
    engine = MagicMock()

    result = await bulk_canonize(engine, "test-user", provider, repo=_make_repo())

    assert result.total == 0
    assert result.canonized == 0
    assert result.failed == 0
    assert result.skipped == 0
    assert result.rate_limited == 0
