from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

load_dotenv()

from database import init_db
from routers import events_router, stream_router


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
    return {"status": "ok", "service": "loglens-api"}


@app.get("/")
async def root():
    return {
        "service": "LogLens API",
        "docs": "/docs",
        "health": "/health",
    }
