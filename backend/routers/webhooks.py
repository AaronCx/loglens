import hashlib
import hmac
import ipaddress
import json
import logging
import socket
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import secrets

import database
from auth import verify_api_key
from database import get_db
from models import Webhook

logger = logging.getLogger("loglens.webhooks")

router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"],
    dependencies=[Depends(verify_api_key)],
)


def validate_webhook_url(url: str) -> None:
    """Reject non-http(s) URLs and targets resolving to internal addresses (SSRF)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=422, detail="Webhook URL must use http or https")
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=422, detail="Webhook URL must include a hostname")
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise HTTPException(status_code=422, detail="Webhook URL hostname could not be resolved")
    for info in addr_infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise HTTPException(
                status_code=422,
                detail="Webhook URL resolves to a disallowed internal address",
            )


class WebhookCreate(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)
    label: str = Field("Alert webhook", max_length=255)
    project_id: Optional[uuid.UUID] = None
    severities: list[str] = Field(default=["critical", "error"])
    services: Optional[list[str]] = None


class WebhookResponse(BaseModel):
    id: uuid.UUID
    url: str
    label: str
    project_id: Optional[uuid.UUID]
    severities: list[str]
    services: Optional[list[str]]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookCreateResponse(WebhookResponse):
    """Returned only on creation: includes the HMAC secret exactly once."""

    secret: Optional[str]


class WebhookUpdate(BaseModel):
    url: Optional[str] = Field(None, max_length=2048)
    label: Optional[str] = Field(None, max_length=255)
    severities: Optional[list[str]] = None
    services: Optional[list[str]] = None
    is_active: Optional[bool] = None


@router.post("", response_model=WebhookCreateResponse, status_code=201)
async def create_webhook(
    body: WebhookCreate,
    db: AsyncSession = Depends(get_db),
):
    validate_webhook_url(body.url)
    webhook = Webhook(
        id=uuid.uuid4(),
        url=body.url,
        label=body.label,
        project_id=body.project_id,
        severities=body.severities,
        services=body.services,
        secret=secrets.token_hex(16),
    )
    db.add(webhook)
    await db.flush()
    await db.refresh(webhook)
    return webhook


@router.get("", response_model=list[WebhookResponse])
async def list_webhooks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Webhook).order_by(Webhook.created_at.desc()))
    return result.scalars().all()


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: uuid.UUID,
    body: WebhookUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Webhook).where(Webhook.id == webhook_id))
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    if body.url is not None:
        validate_webhook_url(body.url)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(webhook, field, value)

    await db.flush()
    await db.refresh(webhook)
    return webhook


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Webhook).where(Webhook.id == webhook_id))
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await db.delete(webhook)


async def fire_webhooks(event_data: dict) -> None:
    """Send webhook notifications for a new event. Called after event creation.

    Runs as a background task, so it opens its own session instead of
    sharing the request-scoped one (which may already be closed/in use).
    """
    severity = event_data.get("severity", "")
    service = event_data.get("service", "")
    project_id = event_data.get("project_id")

    async with database.AsyncSessionLocal() as db:
        query = select(Webhook).where(Webhook.is_active == True)
        result = await db.execute(query)
        webhooks = result.scalars().all()

    async with httpx.AsyncClient(timeout=10.0) as client:
        for wh in webhooks:
            # Filter by severity
            if severity not in (wh.severities or []):
                continue
            # Filter by service if specified
            if wh.services and service not in wh.services:
                continue
            # Filter by project if webhook is project-scoped
            if wh.project_id and str(wh.project_id) != str(project_id):
                continue

            payload = json.dumps(event_data, default=str)
            headers = {"Content-Type": "application/json"}

            if wh.secret:
                signature = hmac.new(
                    wh.secret.encode(), payload.encode(), hashlib.sha256
                ).hexdigest()
                headers["X-LogLens-Signature"] = f"sha256={signature}"

            try:
                await client.post(wh.url, content=payload, headers=headers)
            except Exception as exc:
                logger.warning("Webhook %s failed: %s", wh.id, exc)
