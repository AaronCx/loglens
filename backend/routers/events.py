from fastapi import APIRouter, Depends, HTTPException, Query, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.dialects.postgresql import insert as pg_insert
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any
from datetime import datetime, timezone
import uuid
import os
import asyncio
from slowapi import Limiter
from slowapi.util import get_remote_address

from database import get_db
from models import Event, Severity, ApiKey
from .stream import broadcast_event
from .webhooks import fire_webhooks

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

API_KEY = os.getenv("API_KEY", "dev-secret-key")


async def resolve_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> tuple[str, uuid.UUID | None]:
    """Verify API key. Supports both legacy global key and project-scoped keys."""
    if x_api_key == API_KEY:
        return x_api_key, None

    # Check project-scoped keys
    result = await db.execute(
        select(ApiKey).where(ApiKey.key == x_api_key, ApiKey.is_active == True)
    )
    api_key = result.scalar_one_or_none()
    if api_key:
        return x_api_key, api_key.project_id

    raise HTTPException(status_code=401, detail="Invalid API key")


def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Simple API key check for non-project-scoped endpoints."""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


MAX_METADATA_SIZE = 65_536  # 64 KB

class EventCreate(BaseModel):
    severity: Severity
    service: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1, max_length=10_000)
    stack_trace: Optional[str] = Field(None, max_length=100_000)
    metadata: Optional[dict[str, Any]] = None
    environment: Optional[str] = Field("production", max_length=64)
    timestamp: Optional[datetime] = None

    @field_validator("timestamp", mode="before")
    @classmethod
    def set_timestamp(cls, v):
        return v or datetime.now(timezone.utc)

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata_size(cls, v):
        if v is not None:
            import json
            if len(json.dumps(v)) > MAX_METADATA_SIZE:
                raise ValueError(f"metadata must be smaller than {MAX_METADATA_SIZE} bytes")
        return v


class EventResponse(BaseModel):
    id: uuid.UUID
    timestamp: datetime
    severity: Severity
    service: str
    message: str
    stack_trace: Optional[str]
    metadata: Optional[dict[str, Any]]
    environment: Optional[str]

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=obj.id,
            timestamp=obj.timestamp,
            severity=obj.severity,
            service=obj.service,
            message=obj.message,
            stack_trace=obj.stack_trace,
            metadata=obj.metadata_,
            environment=obj.environment,
        )


class EventsListResponse(BaseModel):
    events: list[EventResponse]
    total: int
    page: int
    page_size: int


class StatsResponse(BaseModel):
    total: int
    by_severity: dict[str, int]
    by_service: dict[str, int]


class TimeSeriesPoint(BaseModel):
    time: str
    info: int
    warning: int
    error: int
    critical: int


INGEST_RATE_LIMIT = os.getenv("INGEST_RATE_LIMIT", "200/minute")


@router.post("/events", response_model=EventResponse, status_code=201)
@limiter.limit(INGEST_RATE_LIMIT)
async def create_event(
    request: Request,
    event: EventCreate,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(resolve_api_key),
):
    _, project_id = auth
    db_event = Event(
        id=uuid.uuid4(),
        timestamp=event.timestamp or datetime.now(timezone.utc),
        severity=event.severity,
        service=event.service,
        message=event.message,
        stack_trace=event.stack_trace,
        metadata_=event.metadata or {},
        environment=event.environment or "production",
        project_id=project_id,
    )
    db.add(db_event)
    await db.flush()
    await db.refresh(db_event)

    event_data = EventResponse.from_orm(db_event)
    event_dict = event_data.model_dump(mode="json")
    event_dict["project_id"] = str(project_id) if project_id else None
    asyncio.create_task(broadcast_event(event_dict))
    asyncio.create_task(fire_webhooks(event_dict, db))

    return event_data


@router.get("/events", response_model=EventsListResponse)
async def list_events(
    severity: Optional[list[Severity]] = Query(None),
    service: Optional[str] = Query(None),
    environment: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(Event).order_by(desc(Event.timestamp))
    count_query = select(func.count(Event.id))

    if severity:
        query = query.where(Event.severity.in_(severity))
        count_query = count_query.where(Event.severity.in_(severity))
    if service:
        query = query.where(Event.service.ilike(f"%{service}%"))
        count_query = count_query.where(Event.service.ilike(f"%{service}%"))
    if environment:
        query = query.where(Event.environment == environment)
        count_query = count_query.where(Event.environment == environment)
    if search:
        query = query.where(Event.message.ilike(f"%{search}%"))
        count_query = count_query.where(Event.message.ilike(f"%{search}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)
    events = result.scalars().all()

    return EventsListResponse(
        events=[EventResponse.from_orm(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventResponse.from_orm(event)


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    total_result = await db.execute(select(func.count(Event.id)))
    total = total_result.scalar_one()

    sev_result = await db.execute(
        select(Event.severity, func.count(Event.id)).group_by(Event.severity)
    )
    by_severity = {row[0].value: row[1] for row in sev_result.all()}

    svc_result = await db.execute(
        select(Event.service, func.count(Event.id))
        .group_by(Event.service)
        .order_by(desc(func.count(Event.id)))
        .limit(10)
    )
    by_service = {row[0]: row[1] for row in svc_result.all()}

    return StatsResponse(total=total, by_severity=by_severity, by_service=by_service)


@router.get("/stats/timeseries", response_model=list[TimeSeriesPoint])
async def get_timeseries(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import text

    sql = text("""
        SELECT
            date_trunc('hour', timestamp) AS hour,
            severity,
            COUNT(*) AS cnt
        FROM events
        WHERE timestamp >= NOW() - make_interval(hours => :hours)
        GROUP BY hour, severity
        ORDER BY hour
    """)

    result = await db.execute(sql, {"hours": hours})
    rows = result.all()

    buckets: dict[str, dict[str, int]] = {}
    for row in rows:
        hour_str = row[0].isoformat() if row[0] else ""
        sev = row[1]
        cnt = row[2]
        if hour_str not in buckets:
            buckets[hour_str] = {"info": 0, "warning": 0, "error": 0, "critical": 0}
        buckets[hour_str][sev] = cnt

    return [
        TimeSeriesPoint(time=hour, **counts)
        for hour, counts in sorted(buckets.items())
    ]


@router.delete("/events/{event_id}", status_code=204)
async def delete_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    await db.delete(event)


RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "30"))


@router.delete("/events/expired", status_code=200)
async def cleanup_expired_events(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    from sqlalchemy import delete, text
    cutoff = text(f"NOW() - make_interval(days => :days)")
    stmt = delete(Event).where(Event.timestamp < cutoff)
    result = await db.execute(stmt, {"days": RETENTION_DAYS})
    return {"deleted": result.rowcount, "retention_days": RETENTION_DAYS}


@router.delete("/events", status_code=204)
async def clear_events(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    from sqlalchemy import delete
    await db.execute(delete(Event))
