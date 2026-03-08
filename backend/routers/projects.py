from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid
import secrets

from database import get_db
from models import Project, ApiKey

router = APIRouter(prefix="/projects", tags=["Projects"])


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    owner_email: Optional[str] = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    owner_email: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    key: str
    label: str
    project_id: uuid.UUID
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class ApiKeyCreate(BaseModel):
    label: str = Field("default", max_length=255)


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    project: ProjectCreate,
    db: AsyncSession = Depends(get_db),
):
    db_project = Project(
        id=uuid.uuid4(),
        name=project.name,
        description=project.description,
        owner_email=project.owner_email,
    )
    db.add(db_project)
    await db.flush()
    await db.refresh(db_project)

    # Auto-create a default API key
    api_key = ApiKey(
        id=uuid.uuid4(),
        key=f"ll_{secrets.token_hex(24)}",
        label="default",
        project_id=db_project.id,
    )
    db.add(api_key)

    return db_project


@router.get("", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    return result.scalars().all()


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/{project_id}/keys", response_model=ApiKeyResponse, status_code=201)
async def create_api_key(
    project_id: uuid.UUID,
    body: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    api_key = ApiKey(
        id=uuid.uuid4(),
        key=f"ll_{secrets.token_hex(24)}",
        label=body.label,
        project_id=project_id,
    )
    db.add(api_key)
    await db.flush()
    await db.refresh(api_key)
    return api_key


@router.get("/{project_id}/keys", response_model=list[ApiKeyResponse])
async def list_api_keys(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ApiKey).where(ApiKey.project_id == project_id).order_by(ApiKey.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/{project_id}/keys/{key_id}", status_code=204)
async def revoke_api_key(
    project_id: uuid.UUID,
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.project_id == project_id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    api_key.is_active = False
