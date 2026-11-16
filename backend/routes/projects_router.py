"""
Projects Router
REST API for project CRUD and tenant management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime, timezone

from database import get_db
from models import Project, Tenant
from utils.rate_limiter import rate_limit_dependency

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


# ── Project CRUD ────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_project(
    tenant_id: str,
    name: str,
    description: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_dependency),
) -> Dict[str, Any]:
    """Create a new project within a tenant."""
    project = Project(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=name,
        description=description,
        status="active",
        metadata=metadata or {},
        created_at=datetime.now(timezone.utc),
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)

    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "tenant_id": tenant_id,
        "status": project.status,
        "created_at": project.created_at.isoformat() if project.created_at else None,
    }


@router.get("")
async def list_projects(
    tenant_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List projects, optionally filtered by tenant."""
    query = select(Project).order_by(desc(Project.created_at))
    if tenant_id:
        query = query.where(Project.tenant_id == tenant_id)

    result = await db.execute(query)
    projects = result.scalars().all()

    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "tenant_id": p.tenant_id,
            "status": p.status,
            "room_count": len(p.rooms) if hasattr(p, "rooms") else 0,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in projects
    ]


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get project details with room count."""
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.rooms))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "tenant_id": project.tenant_id,
        "status": project.status,
        "metadata": project.metadata,
        "rooms": [
            {
                "id": r.id,
                "name": r.name,
                "type": r.room_type,
                "status": r.status,
            }
            for r in (project.rooms or [])
        ],
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
    }


@router.put("/{project_id}")
async def update_project(
    project_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Update project fields."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if name:
        project.name = name
    if description is not None:
        project.description = description
    if status:
        project.status = status
    if metadata is not None:
        project.metadata.update(metadata)

    project.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "id": project.id,
        "name": project.name,
        "status": project.status,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
    }


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Delete a project and all associated rooms."""
    result = await db.execute(
        select(Project).where(Project.id == project_id).options(selectinload(Project.rooms))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    await db.flush()
    return {"status": "deleted", "project_id": project_id}


# ── Tenant Management ─────────────────────────────────────────────────────

@router.post("/tenants", status_code=status.HTTP_201_CREATED)
async def create_tenant(
    name: str,
    slug: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Create a new tenant (organization)."""
    tenant = Tenant(
        id=str(uuid.uuid4()),
        name=name,
        slug=slug or name.lower().replace(" ", "-"),
        status="active",
        metadata=metadata or {},
        created_at=datetime.now(timezone.utc),
    )
    db.add(tenant)
    await db.flush()
    await db.refresh(tenant)

    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "status": tenant.status,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
    }


@router.get("/tenants")
async def list_tenants(
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List all tenants."""
    result = await db.execute(select(Tenant).order_by(desc(Tenant.created_at)))
    tenants = result.scalars().all()

    return [
        {
            "id": t.id,
            "name": t.name,
            "slug": t.slug,
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tenants
    ]


@router.get("/tenants/{tenant_id}")
async def get_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get tenant details with project count."""
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id).options(selectinload(Tenant.projects))
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "status": tenant.status,
        "projects": [
            {"id": p.id, "name": p.name, "status": p.status}
            for p in (tenant.projects or [])
        ],
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
    }
