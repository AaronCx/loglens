from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text, event
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/loglens")

is_supabase = "supabase.com" in DATABASE_URL or "supabase.co" in DATABASE_URL

# Supabase pooler requires SSL; use unnamed prepared statements to avoid conflicts
connect_args = {}
if is_supabase:
    connect_args["ssl"] = "require"
    connect_args["statement_cache_size"] = 0
    connect_args["prepared_statement_cache_size"] = 0
    connect_args["prepared_statement_name_func"] = lambda: ""

engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool if is_supabase else None,
    pool_pre_ping=True,
    echo=False,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    from models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def check_db() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
