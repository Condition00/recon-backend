import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.auth.models import ROLE_ADMIN, User
from app.domains.incidents import controller
from app.domains.incidents.models import IncidentSeverity, IncidentStatus
from app.domains.incidents.schemas import IncidentCreate, IncidentRead, IncidentUpdate
from app.utils.deps import get_current_user, get_db, require_roles

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("/", response_model=IncidentRead)
async def create_incident(
    *,
    db: AsyncSession = Depends(get_db),
    incident_in: IncidentCreate,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new incident report.
    Participants and volunteers can use this endpoint to submit a manual report.
    """
    return await controller.create(db, obj_in=incident_in, reported_by=current_user.id)


@router.get("/", response_model=list[IncidentRead])
async def list_incidents(
    *,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: Optional[IncidentStatus] = None,
    severity: Optional[IncidentSeverity] = None,
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """
    List all incidents. Ops/admin only.
    Can be filtered by status and severity.
    """
    return await controller.list_all(db, skip=skip, limit=limit, status=status, severity=severity)


@router.get("/{incident_id}", response_model=IncidentRead)
async def get_incident(
    *,
    db: AsyncSession = Depends(get_db),
    incident_id: uuid.UUID,
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """
    Get a specific incident by ID. Ops/admin only.
    """
    return await controller.get(db, incident_id=incident_id)


@router.patch("/{incident_id}", response_model=IncidentRead)
async def update_incident(
    *,
    db: AsyncSession = Depends(get_db),
    incident_id: uuid.UUID,
    incident_in: IncidentUpdate,
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """
    Update an incident (e.g. status, assignment, resolution notes). Ops/admin only.
    """
    return await controller.update(db, incident_id=incident_id, obj_in=incident_in)
