"""In-memory event bus for scan progress streaming (F32).

The scan orchestrator runs in a background thread and publishes ScanEvent
objects.  SSE consumers subscribe to a per-scan asyncio.Queue.  Because
the publisher lives in a different thread, we use ``loop.call_soon_threadsafe``
to bridge the gap.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.events import ScanEvent

logger = logging.getLogger(__name__)

_MAX_QUEUE_SIZE = 100

# scan_id -> list of subscriber queues
_subscribers: dict[int, list[asyncio.Queue[ScanEvent]]] = {}

# Reference to the main event loop (set at first subscribe call)
_loop: asyncio.AbstractEventLoop | None = None


def subscribe(scan_id: int) -> asyncio.Queue[ScanEvent]:
    """Create a new subscriber queue for *scan_id*.

    Must be called from the async event loop thread (e.g. an SSE endpoint
    handler).  The loop reference is captured so that ``publish`` can safely
    enqueue from a background thread.
    """
    global _loop
    _loop = asyncio.get_running_loop()

    queue: asyncio.Queue[ScanEvent] = asyncio.Queue(maxsize=_MAX_QUEUE_SIZE)
    _subscribers.setdefault(scan_id, []).append(queue)
    count = len(_subscribers[scan_id])
    logger.debug("scan_bus.subscribe scan_id=%s subscribers=%d", scan_id, count)
    return queue


def unsubscribe(scan_id: int, queue: asyncio.Queue[ScanEvent]) -> None:
    """Remove a subscriber queue for *scan_id*."""
    queues = _subscribers.get(scan_id)
    if queues is None:
        return
    try:
        queues.remove(queue)
    except ValueError:
        pass
    if not queues:
        _subscribers.pop(scan_id, None)
    remaining = len(_subscribers.get(scan_id, []))
    logger.debug("scan_bus.unsubscribe scan_id=%s remaining=%d", scan_id, remaining)


def publish(event: ScanEvent) -> None:
    """Publish *event* to all subscriber queues for ``event.scan_id``.

    This is safe to call from a background thread.  It uses
    ``call_soon_threadsafe`` to schedule puts on the main event loop.
    If a subscriber queue is full the event is silently dropped with a
    warning log.
    """
    queues = _subscribers.get(event.scan_id)
    if not queues:
        return

    loop = _loop
    if loop is None or loop.is_closed():
        logger.warning("scan_bus.publish: no event loop available, dropping event")
        return

    for q in list(queues):
        try:
            loop.call_soon_threadsafe(q.put_nowait, event)
        except asyncio.QueueFull:
            logger.warning(
                "scan_bus.publish: queue full for scan_id=%s, dropping event",
                event.scan_id,
            )
        except RuntimeError:
            # Loop already closed
            logger.warning("scan_bus.publish: event loop closed, dropping event")


def cleanup(scan_id: int) -> None:
    """Remove all subscriber queues for *scan_id*."""
    removed = _subscribers.pop(scan_id, None)
    count = len(removed) if removed else 0
    logger.debug("scan_bus.cleanup scan_id=%s removed=%d", scan_id, count)


def _reset() -> None:
    """Reset all state (for testing only)."""
    global _loop
    _subscribers.clear()
    _loop = None
