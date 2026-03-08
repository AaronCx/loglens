import os
import asyncio

os.environ.setdefault("API_KEY", "test-key")

import pytest

# Create tables using a fresh engine (separate from the app engine)
# This runs once at import time before any tests
from sqlalchemy.ext.asyncio import create_async_engine
from models import Base

_db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/loglens")
_setup_engine = create_async_engine(_db_url)


async def _create_tables():
    async with _setup_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _setup_engine.dispose()


asyncio.run(_create_tables())


@pytest.fixture
def anyio_backend():
    return "asyncio"
