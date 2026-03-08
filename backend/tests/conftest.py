import os

os.environ.setdefault("API_KEY", "test-key")

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"


_initialized = False


@pytest.fixture(autouse=True)
async def _ensure_tables():
    """Create database tables once, running in the test's own event loop."""
    global _initialized
    if not _initialized:
        from database import init_db
        await init_db()
        _initialized = True
