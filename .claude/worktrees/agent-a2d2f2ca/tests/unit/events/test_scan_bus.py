"""Tests for the in-memory scan event bus (F32-T01)."""

from __future__ import annotations

import asyncio

import pytest

from src.domain.events import ScanEvent
from src.events import scan_bus


def _event(scan_id: int = 1, event_type: str = "card_scanned", **kwargs) -> ScanEvent:
    return ScanEvent(
        event_type=event_type,
        scan_id=scan_id,
        timestamp="2026-08-21T10:00:00",
        **kwargs,
    )


@pytest.fixture(autouse=True)
def _reset_bus():
    """Reset bus state before each test."""
    scan_bus._reset()
    yield
    scan_bus._reset()


@pytest.mark.asyncio
class TestScanEventBus:
    """Tests for subscribe / publish / unsubscribe / cleanup lifecycle."""

    async def test_subscribe_and_publish(self):
        queue = scan_bus.subscribe(1)
        event = _event(scan_id=1)
        scan_bus.publish(event)
        # Allow call_soon_threadsafe callback to execute
        await asyncio.sleep(0)
        assert not queue.empty()
        received = queue.get_nowait()
        assert received.event_type == "card_scanned"
        assert received.scan_id == 1

    async def test_multiple_subscribers_receive_same_event(self):
        q1 = scan_bus.subscribe(1)
        q2 = scan_bus.subscribe(1)
        event = _event(scan_id=1, card_name="Bolt")
        scan_bus.publish(event)
        await asyncio.sleep(0)
        r1 = q1.get_nowait()
        r2 = q2.get_nowait()
        assert r1.card_name == "Bolt"
        assert r2.card_name == "Bolt"

    async def test_unsubscribe_removes_queue(self):
        q = scan_bus.subscribe(1)
        scan_bus.unsubscribe(1, q)
        event = _event(scan_id=1)
        scan_bus.publish(event)
        await asyncio.sleep(0)
        assert q.empty()

    async def test_unsubscribe_nonexistent_queue_no_error(self):
        q = scan_bus.subscribe(1)
        other_q: asyncio.Queue = asyncio.Queue()
        # Should not raise
        scan_bus.unsubscribe(1, other_q)
        # Original still works
        scan_bus.publish(_event(scan_id=1))
        await asyncio.sleep(0)
        assert not q.empty()

    async def test_unsubscribe_nonexistent_scan_id_no_error(self):
        scan_bus.unsubscribe(999, asyncio.Queue())

    async def test_cleanup_removes_all_queues(self):
        q1 = scan_bus.subscribe(1)
        q2 = scan_bus.subscribe(1)
        scan_bus.cleanup(1)
        scan_bus.publish(_event(scan_id=1))
        await asyncio.sleep(0)
        assert q1.empty()
        assert q2.empty()

    async def test_cleanup_nonexistent_scan_id_no_error(self):
        scan_bus.cleanup(999)

    async def test_publish_to_empty_subscribers_no_error(self):
        # No subscribers for scan_id=99
        scan_bus.publish(_event(scan_id=99))

    async def test_publish_does_not_cross_scan_ids(self):
        q1 = scan_bus.subscribe(1)
        q2 = scan_bus.subscribe(2)
        scan_bus.publish(_event(scan_id=1))
        await asyncio.sleep(0)
        assert not q1.empty()
        assert q2.empty()

    async def test_queue_bounded_at_max_size(self):
        q = scan_bus.subscribe(1)
        # Fill the queue to capacity
        for i in range(scan_bus._MAX_QUEUE_SIZE):
            scan_bus.publish(_event(scan_id=1, cards_processed=i))
            await asyncio.sleep(0)
        # One more should be dropped (not raise)
        scan_bus.publish(_event(scan_id=1, cards_processed=999))
        await asyncio.sleep(0)
        assert q.qsize() == scan_bus._MAX_QUEUE_SIZE

    async def test_reset_clears_all(self):
        scan_bus.subscribe(1)
        scan_bus.subscribe(2)
        scan_bus._reset()
        assert scan_bus._subscribers == {}
        assert scan_bus._loop is None
