import pytest
import asyncio
from routers.stream import broadcast_event, _subscribers


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_broadcast_event_to_subscribers():
    """Verify broadcast_event delivers data to subscribed queues."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=10)
    _subscribers.add(queue)
    try:
        await broadcast_event({"type": "event", "severity": "error", "message": "test"})
        data = queue.get_nowait()
        assert data["severity"] == "error"
        assert data["message"] == "test"
    finally:
        _subscribers.discard(queue)


@pytest.mark.anyio
async def test_broadcast_drops_full_queues():
    """Verify broadcast removes subscribers with full queues."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=1)
    _subscribers.add(queue)
    try:
        # Fill the queue
        await queue.put({"filler": True})
        # Broadcast should drop this subscriber since queue is full
        await broadcast_event({"type": "event"})
        assert queue not in _subscribers
    finally:
        _subscribers.discard(queue)
