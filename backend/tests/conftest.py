import os

os.environ.setdefault("API_KEY", "test-key")

import pytest
from httpx import ASGITransport, AsyncClient
from main import app
from database import init_db


@pytest.fixture
def anyio_backend():
    return "asyncio"


_initialized = False


@pytest.fixture(autouse=True)
async def _ensure_tables():
    """Create database tables once, running in the test's own event loop."""
    global _initialized
    if not _initialized:
        await init_db()
        _initialized = True


@pytest.fixture
async def client():
    """Shared async client with raise_server_exceptions=False for middleware compat."""
    transport = ASGITransport(app=app, raise_server_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
