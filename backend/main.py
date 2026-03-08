from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

load_dotenv()

from database import init_db, check_db
from routers import events_router, stream_router

RATE_LIMIT = os.getenv("RATE_LIMIT", "100/minute")

limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT])


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

app.include_router(events_router, tags=["Events"])
app.include_router(stream_router, tags=["Stream"])


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
