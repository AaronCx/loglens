import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import secrets

from database import get_db
from models import Webhook

logger = logging.getLogger("loglens.webhooks")

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


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
    secret: Optional[str]

    model_config = {"from_attributes": True}


class WebhookUpdate(BaseModel):
    url: Optional[str] = Field(None, max_length=2048)
    label: Optional[str] = Field(None, max_length=255)
    severities: Optional[list[str]] = None
    services: Optional[list[str]] = None
    is_active: Optional[bool] = None


@router.post("", response_model=WebhookResponse, status_code=201)
async def create_webhook(
    body: WebhookCreate,
    db: AsyncSession = Depends(get_db),
):
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


async def fire_webhooks(event_data: dict, db: AsyncSession) -> None:
    """Send webhook notifications for a new event. Called after event creation."""
    severity = event_data.get("severity", "")
    service = event_data.get("service", "")
    project_id = event_data.get("project_id")

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
