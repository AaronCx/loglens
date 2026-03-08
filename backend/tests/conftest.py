import os
import asyncio

os.environ.setdefault("API_KEY", "test-key")

import pytest


@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    """Create database tables once before the test session."""
    from database import init_db
    asyncio.run(init_db())


@pytest.fixture
def anyio_backend():
    return "asyncio"
