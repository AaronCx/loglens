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
            try:
                async with asyncio.timeout(3):
                    async for chunk in resp.aiter_bytes():
                        first_line += chunk
                        if b"\n\n" in first_line:
                            break
            except TimeoutError:
                pass
            assert b"connected" in first_line
