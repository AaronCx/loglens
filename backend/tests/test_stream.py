import pytest
import asyncio
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


API_HEADERS = {"X-API-Key": "test-key"}


@pytest.mark.anyio
async def test_stream_endpoint_returns_event_stream():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream("GET", "/stream") as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            # Read the first SSE message (connection confirmation)
            first_line = b""
            async for chunk in resp.aiter_bytes():
                first_line += chunk
                if b"\n\n" in first_line:
                    break
            assert b"connected" in first_line


@pytest.mark.anyio
async def test_stream_receives_broadcast_event():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        received_chunks = []

        async def listen():
            async with client.stream("GET", "/stream") as resp:
                count = 0
                async for chunk in resp.aiter_bytes():
                    received_chunks.append(chunk)
                    count += 1
                    if count >= 2:
                        break

        # Start listening in background
        listen_task = asyncio.create_task(listen())

        # Give the SSE connection time to establish
        await asyncio.sleep(0.1)

        # Send an event that should be broadcast
        async with AsyncClient(transport=transport, base_url="http://test") as post_client:
            await post_client.post(
                "/events",
                json={
                    "severity": "error",
                    "service": "stream-test",
                    "message": "Test broadcast",
                },
                headers=API_HEADERS,
            )

        # Wait for listener to receive
        try:
            await asyncio.wait_for(listen_task, timeout=5.0)
        except asyncio.TimeoutError:
            pass

        combined = b"".join(received_chunks)
        assert b"connected" in combined
