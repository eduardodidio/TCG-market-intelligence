"""Tests for src.collectors.price_request_processor."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.collectors.price_request_processor import (
    ProcessingResult,
    process_pending_price_requests,
)


def _make_card_row(card_id=1, name_en="Lightning Bolt", name_pt=None, set_code="m10", cn="146"):
    row = MagicMock()
    row.id = card_id
    row.name_en = name_en
    row.name_pt = name_pt
    row.set_code = set_code
    row.collector_number = cn
    return row


def _make_request_row(req_id=1, card_id=1, status="pending"):
    row = MagicMock()
    row.id = req_id
    row.card_id = card_id
    row.status = status
    row.attempts = 0
    return row


def _make_observation(price=12.50):
    obs = MagicMock()
    obs.median_price = Decimal(str(price))
    return obs


def _patch_deps(mock_repo, mock_provider, mock_fetch_liga=None):
    """Create context managers for patching the lazy imports."""
    mock_repo_cls = MagicMock(return_value=mock_repo)
    mock_provider_cls = MagicMock(return_value=mock_provider)

    patches = [
        patch("src.database.repository.Repository", mock_repo_cls),
        patch("src.providers.liga.provider.LigaMagicProvider", mock_provider_cls),
    ]
    if mock_fetch_liga is not None:
        patches.append(patch("src.collectors.liga_sweep._fetch_liga_price", mock_fetch_liga))
    return patches


@pytest.mark.asyncio
async def test_processes_pending_requests():
    """Processes pending requests and returns correct counts."""
    request = _make_request_row(req_id=1, card_id=10)
    card = _make_card_row(card_id=10)
    obs = _make_observation(12.50)

    mock_repo = MagicMock()
    mock_repo.get_pending_price_requests.return_value = [request]
    mock_repo.get_card_by_id.return_value = card

    mock_provider = MagicMock()
    mock_provider.initialize = AsyncMock()
    mock_provider.close = AsyncMock()

    mock_fetch = AsyncMock(return_value=(obs, "https://ligamagic.com/page"))

    patches = _patch_deps(mock_repo, mock_provider, mock_fetch)
    for p in patches:
        p.start()
    try:
        result = await process_pending_price_requests(db_url="sqlite:///test.db", limit=10, delay=0)
    finally:
        for p in patches:
            p.stop()

    assert isinstance(result, ProcessingResult)
    assert result.total == 1
    assert result.completed == 1
    assert result.failed == 0
    mock_repo.update_price_request_status.assert_any_call(1, "processing")
    mock_repo.update_price_request_status.assert_any_call(
        1, "completed", result_price=obs.median_price
    )
    mock_repo.insert_price_observations.assert_called_once_with([obs])


@pytest.mark.asyncio
async def test_handles_liga_error():
    """Marks request as failed when Liga raises an error."""
    from src.providers.liga.exceptions import LigaError

    request = _make_request_row(req_id=2, card_id=20)
    card = _make_card_row(card_id=20, name_en="Counterspell")

    mock_repo = MagicMock()
    mock_repo.get_pending_price_requests.return_value = [request]
    mock_repo.get_card_by_id.return_value = card

    mock_provider = MagicMock()
    mock_provider.initialize = AsyncMock()
    mock_provider.close = AsyncMock()

    mock_fetch = AsyncMock(side_effect=LigaError("Rate limited"))

    patches = _patch_deps(mock_repo, mock_provider, mock_fetch)
    for p in patches:
        p.start()
    try:
        result = await process_pending_price_requests(db_url="sqlite:///test.db", limit=10, delay=0)
    finally:
        for p in patches:
            p.stop()

    assert result.completed == 0
    assert result.failed == 1
    mock_repo.update_price_request_status.assert_any_call(2, "failed", error_message="Rate limited")


@pytest.mark.asyncio
async def test_respects_limit():
    """Only processes up to `limit` requests."""
    card = _make_card_row()
    obs = _make_observation(5.0)

    mock_repo = MagicMock()
    mock_repo.get_pending_price_requests.return_value = [
        _make_request_row(req_id=i, card_id=i) for i in range(1, 3)
    ]
    mock_repo.get_card_by_id.return_value = card

    mock_provider = MagicMock()
    mock_provider.initialize = AsyncMock()
    mock_provider.close = AsyncMock()

    mock_fetch = AsyncMock(return_value=(obs, None))

    patches = _patch_deps(mock_repo, mock_provider, mock_fetch)
    for p in patches:
        p.start()
    try:
        result = await process_pending_price_requests(db_url="sqlite:///test.db", limit=2, delay=0)
    finally:
        for p in patches:
            p.stop()

    assert result.total == 2
    assert result.completed == 2
    mock_repo.get_pending_price_requests.assert_called_once_with(limit=2)


@pytest.mark.asyncio
async def test_skips_cards_without_names():
    """Marks request as failed if card has no name."""
    request = _make_request_row(req_id=5, card_id=50)
    card = _make_card_row(card_id=50, name_en=None, name_pt=None)

    mock_repo = MagicMock()
    mock_repo.get_pending_price_requests.return_value = [request]
    mock_repo.get_card_by_id.return_value = card

    mock_provider = MagicMock()
    mock_provider.initialize = AsyncMock()
    mock_provider.close = AsyncMock()

    patches = _patch_deps(mock_repo, mock_provider)
    for p in patches:
        p.start()
    try:
        result = await process_pending_price_requests(db_url="sqlite:///test.db", limit=10, delay=0)
    finally:
        for p in patches:
            p.stop()

    assert result.failed == 1
    assert result.completed == 0
    mock_repo.update_price_request_status.assert_called_with(
        5, "failed", error_message="Card has no name"
    )


@pytest.mark.asyncio
async def test_no_pending_returns_empty():
    """Returns zero counts when no pending requests exist."""
    mock_repo = MagicMock()
    mock_repo.get_pending_price_requests.return_value = []

    patches = [patch("src.database.repository.Repository", MagicMock(return_value=mock_repo))]
    for p in patches:
        p.start()
    try:
        result = await process_pending_price_requests(db_url="sqlite:///test.db", limit=10, delay=0)
    finally:
        for p in patches:
            p.stop()

    assert result.total == 0
    assert result.completed == 0
    assert result.failed == 0


@pytest.mark.asyncio
async def test_card_not_found():
    """Marks request as failed if card doesn't exist in DB."""
    request = _make_request_row(req_id=7, card_id=999)

    mock_repo = MagicMock()
    mock_repo.get_pending_price_requests.return_value = [request]
    mock_repo.get_card_by_id.return_value = None

    mock_provider = MagicMock()
    mock_provider.initialize = AsyncMock()
    mock_provider.close = AsyncMock()

    patches = _patch_deps(mock_repo, mock_provider)
    for p in patches:
        p.start()
    try:
        result = await process_pending_price_requests(db_url="sqlite:///test.db", limit=10, delay=0)
    finally:
        for p in patches:
            p.stop()

    assert result.failed == 1
    mock_repo.update_price_request_status.assert_called_with(
        7, "failed", error_message="Card not found in database"
    )


@pytest.mark.asyncio
async def test_no_price_found_still_completes():
    """When Liga returns None, request is still marked completed."""
    request = _make_request_row(req_id=3, card_id=30)
    card = _make_card_row(card_id=30)

    mock_repo = MagicMock()
    mock_repo.get_pending_price_requests.return_value = [request]
    mock_repo.get_card_by_id.return_value = card

    mock_provider = MagicMock()
    mock_provider.initialize = AsyncMock()
    mock_provider.close = AsyncMock()

    mock_fetch = AsyncMock(return_value=None)

    patches = _patch_deps(mock_repo, mock_provider, mock_fetch)
    for p in patches:
        p.start()
    try:
        result = await process_pending_price_requests(db_url="sqlite:///test.db", limit=10, delay=0)
    finally:
        for p in patches:
            p.stop()

    assert result.completed == 1
    assert result.failed == 0
    mock_repo.update_price_request_status.assert_any_call(
        3, "completed", error_message="No price found on LigaMagic"
    )
