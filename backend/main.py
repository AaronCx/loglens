from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import os
import time
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import structlog

load_dotenv()

from logging_config import setup_logging
setup_logging()

from database import init_db, check_db, AsyncSessionLocal
from routers import events_router, stream_router, projects_router, webhooks_router

logger = structlog.get_logger("loglens")

RATE_LIMIT = os.getenv("RATE_LIMIT", "100/minute")

limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT])


RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "30"))
CLEANUP_INTERVAL_HOURS = int(os.getenv("CLEANUP_INTERVAL_HOURS", "6"))


async def _periodic_cleanup():
    from sqlalchemy import delete, text
    from models import Event

    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_HOURS * 3600)
        try:
            async with AsyncSessionLocal() as session:
                cutoff = text("NOW() - make_interval(days => :days)")
                result = await session.execute(
                    delete(Event).where(Event.timestamp < cutoff),
                    {"days": RETENTION_DAYS},
                )
                await session.commit()
                if result.rowcount > 0:
                    logger.info("Retention cleanup: deleted %d expired events", result.rowcount)
        except Exception as exc:
            logger.warning("Retention cleanup failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    cleanup_task = asyncio.create_task(_periodic_cleanup())
    yield
    cleanup_task.cancel()


app = FastAPI(
    title="LogLens API",
    description="Real-time error logging and monitoring API",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again later."},
        headers={"Retry-After": str(exc.detail)},
    )


ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.error("request", method=request.method, path=request.url.path, status=500, duration_ms=duration_ms)
        raise
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    if request.url.path not in ("/health", "/stream"):
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
    return response


app.include_router(events_router, tags=["Events"])
app.include_router(stream_router, tags=["Stream"])
app.include_router(projects_router)
app.include_router(webhooks_router)


@app.get("/health")
async def health():
    db_ok = await check_db()
    status = "ok" if db_ok else "degraded"
    return {"status": status, "service": "loglens-api", "database": "connected" if db_ok else "unreachable"}


@app.get("/")
async def root():
    return {
        "service": "LogLens API",
        "docs": "/docs",
        "health": "/health",
    }
