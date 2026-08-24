"""Tests for scan orchestrator event publishing (F32-T02).

Verifies that run_scan publishes ScanEvent objects to the event bus
at each stage: scan_started, card_scanned (per card), scan_complete.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from src.collectors.scan import run_scan
from src.domain.models import JsonLdPrice
from src.events import scan_bus


def _card_entry(
    external_id: str = "1000",
    slug: str = "lightning-bolt",
    card_id: int = 100,
    set_code: str = "LEA",
    name_en: str = "Lightning Bolt",
) -> dict:
    return {
        "external_id": external_id,
        "slug": slug,
        "card_id": card_id,
        "set_code": set_code,
        "name_en": name_en,
    }


def _jsonld_price(
    price: Decimal | None = Decimal("12.50"),
    currency: str = "BRL",
    availability: str = "InStock",
) -> JsonLdPrice:
    return JsonLdPrice(price=price, currency=currency, availability=availability)


def _setup_repo_mock(repo_mock, entries, insert_return=1):
    repo_mock.create_scan_run.return_value = 1
    repo_mock.update_scan_run.return_value = None
    repo_mock.get_cards_for_scan.return_value = entries
    repo_mock.insert_price_observations.return_value = insert_return

    def _build_get_scan_run(run_id):
        merged: dict = {
            "id": 1,
            "scan_type": "collection",
            "filters_json": "{}",
            "status": "pending",
            "cards_total": 0,
            "cards_processed": 0,
            "cards_failed": 0,
            "observations_saved": 0,
            "error_summary": None,
            "started_at": None,
            "finished_at": None,
            "created_at": None,
        }
        for call in repo_mock.update_scan_run.call_args_list:
            merged.update(call[1])
        return merged

    repo_mock.get_scan_run.side_effect = _build_get_scan_run


@pytest.fixture(autouse=True)
def _reset_bus():
    scan_bus._reset()
    yield
    scan_bus._reset()


@pytest.mark.asyncio
class TestScanOrchestratorEvents:
    """Tests that scan events are published correctly."""

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_publishes_scan_started_event(self, MockRepo, MockProvider):
        entries = [_card_entry(external_id="1001")]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries)

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(return_value=_jsonld_price())
        provider.close = AsyncMock()

        # Subscribe to events
        queue = scan_bus.subscribe(1)

        await run_scan(db_url="sqlite:///:memory:", concurrency=1, run_id=1)

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        started = [e for e in events if e.event_type == "scan_started"]
        assert len(started) == 1
        assert started[0].cards_total == 1
        assert started[0].scan_id == 1

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_publishes_card_scanned_events(self, MockRepo, MockProvider):
        entries = [
            _card_entry(external_id="1001", name_en="Card A"),
            _card_entry(external_id="1002", name_en="Card B"),
        ]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries)

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(return_value=_jsonld_price(Decimal("10.00")))
        provider.close = AsyncMock()

        queue = scan_bus.subscribe(1)

        await run_scan(db_url="sqlite:///:memory:", concurrency=1, run_id=1)

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        card_events = [e for e in events if e.event_type == "card_scanned"]
        assert len(card_events) == 2
        assert all(e.price_found is True for e in card_events)
        assert all(e.price == Decimal("10.00") for e in card_events)

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_publishes_scan_complete_event(self, MockRepo, MockProvider):
        entries = [_card_entry(external_id="1001")]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries)

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(return_value=_jsonld_price())
        provider.close = AsyncMock()

        queue = scan_bus.subscribe(1)

        await run_scan(db_url="sqlite:///:memory:", concurrency=1, run_id=1)

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        complete = [e for e in events if e.event_type == "scan_complete"]
        assert len(complete) == 1
        assert complete[0].cards_processed == 1
        assert complete[0].cards_total == 1
        assert complete[0].observations_saved == 1

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_publishes_error_events(self, MockRepo, MockProvider):
        entries = [
            _card_entry(external_id="1001", name_en="Fail Card"),
            _card_entry(external_id="1002", name_en="OK Card"),
        ]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries)

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(
            side_effect=[
                RuntimeError("Timeout"),
                _jsonld_price(Decimal("5.00")),
            ]
        )
        provider.close = AsyncMock()

        queue = scan_bus.subscribe(1)

        await run_scan(db_url="sqlite:///:memory:", concurrency=1, run_id=1)

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        card_events = [e for e in events if e.event_type == "card_scanned"]
        assert len(card_events) == 2
        error_events = [e for e in card_events if e.error is not None]
        assert len(error_events) == 1
        assert "Timeout" in error_events[0].error

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_cleanup_called_after_scan(self, MockRepo, MockProvider):
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries=[])

        provider = MockProvider.return_value
        provider.close = AsyncMock()

        queue = scan_bus.subscribe(1)

        await run_scan(db_url="sqlite:///:memory:", concurrency=1, run_id=1)

        # After run_scan finishes (includes 5s delay + cleanup), the queue
        # should be unsubscribed
        assert scan_bus._subscribers.get(1) is None or queue not in scan_bus._subscribers.get(1, [])

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_no_price_card_scanned_event(self, MockRepo, MockProvider):
        entries = [_card_entry(external_id="1001", name_en="Forest")]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries)

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(return_value=_jsonld_price(price=None))
        provider.close = AsyncMock()

        queue = scan_bus.subscribe(1)

        await run_scan(db_url="sqlite:///:memory:", concurrency=1, run_id=1)

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        card_events = [e for e in events if e.event_type == "card_scanned"]
        assert len(card_events) == 1
        assert card_events[0].price_found is False
        assert card_events[0].card_name == "Forest"
