import os

os.environ.setdefault("API_KEY", "test-key")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import NullPool

# Override engine with NullPool BEFORE importing app (avoids event-loop affinity issues)
import database
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

database.engine = create_async_engine(
    database.DATABASE_URL,
    poolclass=NullPool,
    echo=False,
)
database.AsyncSessionLocal = async_sessionmaker(
    database.engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

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
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
