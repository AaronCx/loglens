import asyncio
import json
from typing import AsyncGenerator
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

# Global set of active SSE queues
_subscribers: set[asyncio.Queue] = set()


async def broadcast_event(event_data: dict):
    """Broadcast a new event to all SSE subscribers."""
    dead = set()
    for queue in _subscribers:
        try:
            queue.put_nowait(event_data)
        except asyncio.QueueFull:
            dead.add(queue)
    for q in dead:
        _subscribers.discard(q)


async def _event_generator(queue: asyncio.Queue) -> AsyncGenerator[str, None]:
    # Send a connection confirmation
    yield f"data: {json.dumps({'type': 'connected'})}\n\n"

    try:
        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=30.0)
                payload = json.dumps({"type": "event", "data": data})
                yield f"data: {payload}\n\n"
            except asyncio.TimeoutError:
                # Send keepalive ping
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        _subscribers.discard(queue)


@router.get("/stream")
async def event_stream():
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.add(queue)

    return StreamingResponse(
        _event_generator(queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
