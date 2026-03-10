from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
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
from routers import events_router, projects_router, webhooks_router

logger = structlog.get_logger("loglens")

RATE_LIMIT = os.getenv("RATE_LIMIT", "100/minute")

limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT])

RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "30"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


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

class LogRequestsMiddleware:
    """Pure ASGI middleware for request logging (avoids BaseHTTPMiddleware ExceptionGroup issues)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            logger.error("request", method=request.method, path=request.url.path, status=500, duration_ms=duration_ms)
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        if request.url.path not in ("/health",):
            logger.info(
                "request",
                method=request.method,
                path=request.url.path,
                status=status_code,
                duration_ms=duration_ms,
            )


app.add_middleware(LogRequestsMiddleware)


app.include_router(events_router, tags=["Events"])
app.include_router(projects_router)
app.include_router(webhooks_router)


CRON_SECRET = os.getenv("CRON_SECRET", "")


@app.get("/health")
async def health():
    db_ok = await check_db()
    status = "ok" if db_ok else "degraded"
    return {"status": status, "service": "loglens-api", "database": "connected" if db_ok else "unreachable"}


@app.get("/cron/cleanup")
async def cron_cleanup(request: Request):
    """Called by Vercel Cron to delete events older than RETENTION_DAYS."""
    auth = request.headers.get("authorization", "")
    if CRON_SECRET and auth != f"Bearer {CRON_SECRET}":
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    from sqlalchemy import delete, text
    from models import Event

    async with AsyncSessionLocal() as session:
        cutoff = text("NOW() - make_interval(days => :days)")
        result = await session.execute(
            delete(Event).where(Event.timestamp < cutoff),
            {"days": RETENTION_DAYS},
        )
        await session.commit()
        deleted = result.rowcount
        logger.info("Cron cleanup: deleted %d expired events", deleted)
        return {"deleted": deleted, "retention_days": RETENTION_DAYS}


@app.get("/")
async def root():
    return {
        "service": "LogLens API",
        "docs": "/docs",
        "health": "/health",
    }
